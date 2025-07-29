use bytes::Bytes;
use http::{HeaderMap, Method, Request, Response, Uri};
use http_cache_semantics::{AfterResponse, BeforeRequest, CacheOptions, CachePolicy};
use lru::LruCache;
use std::{
    num::NonZero,
    sync::{Arc, Mutex},
    time::{Duration, SystemTime},
};

#[derive(Debug)]
pub enum CacheBefore {
    /// The cache is stale or missing, so we need to make a request. Note that CachedItem
    /// may contain a stale cache item and must be returned in `after_request`.
    Request(http::Request<Vec<u8>>, CachedItem),
    /// The cache is fresh, so we can return the response
    Response(http::Response<Bytes>),
}

#[derive(Debug)]
pub struct CachedItem {
    maybe_item: Option<(Arc<CachePolicy>, Bytes)>,
}

impl CachedItem {
    fn none() -> Self {
        Self { maybe_item: None }
    }

    fn some(policy: Arc<CachePolicy>, body: Bytes) -> Self {
        Self {
            maybe_item: Some((policy, body)),
        }
    }
}

struct CacheItems<T> {
    items: LruCache<Uri, (T, Bytes)>,
    byte_size: usize,
    max_byte_size: usize,
}

impl<T> CacheItems<T> {
    fn new(capacity: NonZero<usize>, max_byte_size: usize) -> Self {
        Self {
            items: LruCache::new(capacity),
            byte_size: 0,
            max_byte_size,
        }
    }

    fn insert(&mut self, uri: Uri, policy: T, body: Bytes) {
        if self.items.is_empty() {
            debug_assert!(self.byte_size == 0);
        }
        let body_len = body.len();
        if let Some((_, old_body)) = self.items.push(uri, (policy, body)) {
            self.byte_size = self.byte_size.saturating_sub(old_body.1.len());
        }
        self.byte_size = self.byte_size.saturating_add(body_len);
        while self.byte_size > self.max_byte_size {
            if let Some((_, old_body)) = self.items.pop_lru() {
                self.byte_size = self.byte_size.saturating_sub(old_body.1.len());
            } else {
                return;
            }
        }
    }

    fn get(&mut self, uri: &Uri) -> Option<&(T, Bytes)> {
        self.items.get(uri)
    }

    fn get_mut(&mut self, uri: &Uri) -> Option<(&mut T, &Bytes)> {
        let entry = self.items.get_mut(uri)?;
        Some((&mut entry.0, &entry.1))
    }
}

#[derive(Clone)]
pub struct Cache {
    cache_options: CacheOptions,
    cache: Arc<Mutex<CacheItems<Arc<CachePolicy>>>>,
}

impl Cache {
    pub fn new() -> Self {
        Self {
            cache_options: CacheOptions {
                shared: false,
                // Immutable objects should be cached for 24 hours
                immutable_min_time_to_live: Duration::from_secs(86_400),
                ..Default::default()
            },
            cache: Arc::new(Mutex::new(CacheItems::new(
                NonZero::new(100).unwrap(),
                10 * 1024 * 1024,
            ))),
        }
    }

    #[cfg(test)]
    pub fn get_cache_body(&self, url: &Uri) -> Option<(bool, Vec<u8>)> {
        let mut cache = self.cache.lock().unwrap();
        let entry = cache.get(url);
        if let Some((policy, body)) = entry {
            let state = policy.is_stale(SystemTime::now());
            // NOTE: inefficient, for testing only
            return Some((state, body.to_vec()));
        }
        None
    }

    #[cfg(test)]
    pub fn clear(&self) {
        let mut cache = self.cache.lock().unwrap();
        cache.items.clear();
        cache.byte_size = 0;
    }

    pub fn before_request(
        &self,
        allow_cache: bool,
        method: &Method,
        url: &Uri,
        headers: &HeaderMap,
        body: Vec<u8>,
    ) -> CacheBefore {
        let mut req = Request::new(body);
        *req.method_mut() = method.clone();
        *req.uri_mut() = url.clone();
        *req.headers_mut() = headers.clone();

        // Only cache GET requests
        if !allow_cache || method != Method::GET {
            return CacheBefore::Request(req, CachedItem::none());
        }

        let now = SystemTime::now();
        let mut cache = self.cache.lock().unwrap();
        if let Some((policy, body)) = cache.get(url) {
            match policy.before_request(&req, now) {
                BeforeRequest::Fresh(parts) => {
                    // Fresh response from cache
                    CacheBefore::Response(Response::from_parts(parts, body.clone()))
                }
                BeforeRequest::Stale { request, .. } => {
                    // Stale response, return the cached item that we need to revalidate
                    *req.uri_mut() = request.uri;
                    *req.headers_mut() = request.headers;
                    *req.method_mut() = request.method;
                    CacheBefore::Request(req, CachedItem::some(policy.clone(), body.clone()))
                }
            }
        } else {
            CacheBefore::Request(req, CachedItem::none())
        }
    }

    pub fn after_request(
        &self,
        allow_cache: bool,
        method: Method,
        uri: Uri,
        headers: HeaderMap,
        res: &mut http::Response<Bytes>,
        cached_item: CachedItem,
    ) {
        // Only cache GET requests
        if !allow_cache || method != Method::GET {
            return;
        }

        let now = SystemTime::now();
        let mut cache = self.cache.lock().unwrap();

        let mut req = Request::new(());
        *req.method_mut() = method;
        *req.uri_mut() = uri.clone();
        *req.headers_mut() = headers;

        if let Some((policy, body)) = cached_item.maybe_item {
            let entry = cache.get_mut(&uri);
            let parts = match policy.after_response(&req, res, now) {
                AfterResponse::NotModified(new_policy, parts) => {
                    // Not modified, return the cached response and update the
                    // policy and response body
                    body.clone_into(res.body_mut());

                    // TODO: Can new_policy.is_storable() be false?
                    if let Some((old_policy, _)) = entry {
                        *old_policy = Arc::new(new_policy);
                    } else {
                        cache.insert(uri, Arc::new(new_policy), body);
                    }
                    parts
                }
                AfterResponse::Modified(new_policy, parts) => {
                    // Modified, update the cache, but not the response body

                    // TODO: Can new_policy.is_storable() be false?
                    cache.insert(uri, Arc::new(new_policy), res.body().clone());
                    parts
                }
            };
            *res.headers_mut() = parts.headers;
            *res.status_mut() = parts.status;
            *res.version_mut() = parts.version;
            *res.extensions_mut() = parts.extensions;
        } else {
            // We had no cached item at the start, but we might have raced another
            let policy = CachePolicy::new_options(&req, res, now, self.cache_options);
            if policy.is_storable() {
                cache.insert(uri, Arc::new(policy), res.body().clone());
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use http::*;
    use std::str::FromStr;

    use super::*;

    fn get_google() -> (Method, Uri, HeaderMap, Vec<u8>) {
        let method = Method::GET;
        let uri = Uri::from_str("https://www.google.com").unwrap();
        let headers = HeaderMap::new();
        let body = vec![];
        (method, uri, headers, body)
    }

    fn cache_control<T>(resp: &mut Response<T>, value: &str) {
        resp.headers_mut().insert(
            HeaderName::from_static("cache-control"),
            HeaderValue::from_str(value).unwrap(),
        );
    }

    fn etag<T>(resp: &mut Response<T>, value: &str) {
        resp.headers_mut().insert(
            HeaderName::from_static("etag"),
            HeaderValue::from_str(value).unwrap(),
        );
    }

    fn response(status: StatusCode, body: &str) -> Response<Bytes> {
        let mut resp = Response::new(body.as_bytes().to_vec().into());
        *resp.status_mut() = status;
        resp
    }

    #[test]
    fn test_cache_byte_size_eviction() {
        let mut cache_items = CacheItems::<()>::new(NonZero::new(100).unwrap(), 1024 * 1024);
        cache_items.insert(
            Uri::from_str("https://www.google.com").unwrap(),
            (),
            vec![0; 1024 * 1024].into(),
        );
        assert_eq!(cache_items.byte_size, 1024 * 1024);
        assert_eq!(cache_items.items.len(), 1);
        cache_items.insert(
            Uri::from_str("https://www.example.com").unwrap(),
            (),
            vec![0; 1].into(),
        );
        assert_eq!(cache_items.byte_size, 1);
        assert_eq!(cache_items.items.len(), 1);
        cache_items.insert(
            Uri::from_str("https://www.google.com").unwrap(),
            (),
            vec![0; 1024 * 1024].into(),
        );
        assert_eq!(cache_items.byte_size, 1024 * 1024);
        assert_eq!(cache_items.items.len(), 1);
    }

    #[test]
    fn test_cache_capacity_eviction() {
        let mut cache_items = CacheItems::<()>::new(NonZero::new(100).unwrap(), 1024 * 1024);
        for i in 0..120 {
            cache_items.insert(
                Uri::from_str(&format!("https://www.example.com/{}", i)).unwrap(),
                (),
                vec![0; 10].into(),
            );
        }
        assert_eq!(cache_items.byte_size, 1000);
        assert_eq!(cache_items.items.len(), 100);
    }

    #[test]
    fn test_cache() {
        let cache = Cache::new();
        let (method, uri, headers, body) = get_google();
        let before = cache.before_request(true, &method, &uri, &headers, body);
        let CacheBefore::Request(req, cached_item) = before else {
            panic!("Expected a request {before:?}");
        };

        assert_eq!(req.method(), &method);
        assert_eq!(req.uri(), &uri);
        assert_eq!(req.headers(), &headers);
        assert!(cached_item.maybe_item.is_none());

        let mut resp = response(StatusCode::OK, "this is a response");
        cache_control(&mut resp, "max-age=3600");
        etag(&mut resp, "\"1234567890\"");
        cache.after_request(
            true,
            method.clone(),
            uri.clone(),
            headers.clone(),
            &mut resp,
            cached_item,
        );

        let (method, uri, headers, body) = get_google();
        let after = cache.before_request(true, &method, &uri, &headers, body);

        let CacheBefore::Response(resp) = after else {
            panic!("Expected a response {after:?}");
        };
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(resp.body(), "this is a response".as_bytes());
        assert_eq!(
            resp.headers().get("etag"),
            Some(&HeaderValue::from_str("\"1234567890\"").unwrap())
        );
        assert_eq!(
            resp.headers().get("cache-control"),
            Some(&HeaderValue::from_str("max-age=3600").unwrap())
        );
    }

    #[test]
    fn test_cache_not_modified() {
        let cache = Cache::new();

        // First request, clean cache

        let (method, uri, headers, body) = get_google();
        let before = cache.before_request(true, &method, &uri, &headers, body);
        let CacheBefore::Request(req, cached_item) = before else {
            panic!("Expected a request {before:?}");
        };

        assert_eq!(req.method(), &method);
        assert_eq!(req.uri(), &uri);
        assert_eq!(req.headers(), &headers);
        assert!(cached_item.maybe_item.is_none());

        let mut resp = response(StatusCode::OK, "contents!");
        cache_control(
            &mut resp,
            "max-age=0, must-revalidate, stale-while-revalidate=86400",
        );
        etag(&mut resp, "\"1234567890\"");
        cache.after_request(
            true,
            method.clone(),
            uri.clone(),
            headers.clone(),
            &mut resp,
            cached_item,
        );

        let (state, body) = cache.get_cache_body(&uri).unwrap();
        assert!(state);
        assert_eq!(body, "contents!".as_bytes());

        // Must-revalidate, so we need to revalidate the cache

        let (method, uri, headers, body) = get_google();
        let after = cache.before_request(true, &method, &uri, &headers, body);
        let CacheBefore::Request(req, cached_item) = after else {
            panic!("Expected a request {after:?}");
        };
        assert_eq!(req.method(), &Method::GET);
        assert_eq!(req.uri(), &uri);
        assert_eq!(
            req.headers().get("if-none-match"),
            Some(&HeaderValue::from_str("\"1234567890\"").unwrap())
        );

        let mut resp = response(StatusCode::NOT_MODIFIED, "");
        cache_control(
            &mut resp,
            "max-age=0, must-revalidate, stale-while-revalidate=86400",
        );
        etag(&mut resp, "\"1234567890\"");
        cache.after_request(
            true,
            method.clone(),
            uri.clone(),
            headers.clone(),
            &mut resp,
            cached_item,
        );

        let (state, body) = cache.get_cache_body(&uri).unwrap();
        assert!(state);
        assert_eq!(body, "contents!".as_bytes());

        // Test what happens when the cache evicts during the request

        let (method, uri, headers, body) = get_google();
        let after = cache.before_request(true, &method, &uri, &headers, body);
        let CacheBefore::Request(req, cached_item) = after else {
            panic!("Expected a request {after:?}");
        };
        assert_eq!(req.method(), &Method::GET);
        assert_eq!(req.uri(), &uri);
        assert_eq!(
            req.headers().get("if-none-match"),
            Some(&HeaderValue::from_str("\"1234567890\"").unwrap())
        );

        cache.clear();

        let mut resp = response(StatusCode::NOT_MODIFIED, "");
        cache_control(
            &mut resp,
            "max-age=0, must-revalidate, stale-while-revalidate=86400",
        );
        etag(&mut resp, "\"1234567890\"");
        cache.after_request(
            true,
            method.clone(),
            uri.clone(),
            headers.clone(),
            &mut resp,
            cached_item,
        );

        assert_eq!(resp.body(), "contents!".as_bytes());

        let (state, body) = cache.get_cache_body(&uri).unwrap();
        assert!(state);
        assert_eq!(body, "contents!".as_bytes());
    }
}
