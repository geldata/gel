// See https://nextjs.org/docs/app/api-reference/config/next-config-js/redirects
module.exports = [
  {
    source: "/guides/cheatsheet/:path*",
    destination: "/resources/cheatsheets/:path*",
    permanent: true,
  },
  {
    source: "/guides/ai/:path*",
    destination: "/ai/:path*",
    permanent: true,
  },
  {
    source: "/changelog/6_x",
    destination: "/resources/changelog/6_x",
    permanent: true,
  },
  {
    source: "/database/:path*",
    destination: "/reference/:path*",
    permanent: false,
  },
  {
    source: "/guides/:path*",
    destination: "/resources/guides/:path*",
    permanent: false,
  },
  {
    source: "/reference/clients/connection",
    destination: "/reference/connection",
    permanent: false,
  },
  {
    source: "/reference/reference/bindings/datetime",
    destination: "/reference/clients/datetime",
    permanent: false,
  },
  {
    source: "/reference/reference/bindings",
    destination: "/reference/clients",
    permanent: false,
  },
  {
    source: "/reference/clients/go/:path*",
    destination: "https://pkg.go.dev/github.com/geldata/gel-go",
    permanent: false,
  },
  {
    source: "/reference/clients/rust/:path*",
    destination: "https://docs.rs/gel-tokio",
    permanent: false,
  },
  {
    source: "/reference/clients/js/delete#delete",
    destination: "/reference/clients/js/querybuilder",
    permanent: false,
  },
  {
    source: "/reference/clients/js/driver",
    destination: "/reference/clients/js",
    permanent: false,
  },
  {
    source: "/reference/clients/js/for",
    destination: "/reference/clients/js/querybuilder#for",
    permanent: false,
  },
  {
    source: "/reference/clients/js/funcops",
    destination: "/reference/clients/js/querybuilder#functions-and-operators",
    permanent: false,
  },
  {
    source: "/reference/clients/js/group",
    destination: "/reference/clients/js/querybuilder#group",
    permanent: false,
  },
  {
    source: "/reference/clients/js/insert",
    destination: "/reference/clients/js/querybuilder#insert",
    permanent: false,
  },
  {
    source: "/reference/clients/js/literals",
    destination: "/reference/clients/js/querybuilder#types-and-literals",
    permanent: false,
  },
  {
    source: "/reference/clients/js/objects",
    destination: "/reference/clients/js/querybuilder#objects-and-paths",
    permanent: false,
  },
  {
    source: "/reference/clients/js/parameters",
    destination: "/reference/clients/js/querybuilder#parameters",
    permanent: false,
  },
  {
    source: "/reference/clients/js/select",
    destination: "/reference/clients/js/querybuilder#select",
    permanent: false,
  },
  {
    source: "/reference/clients/js/types",
    destination: "/reference/clients/js/querybuilder#types-and-literals",
    permanent: false,
  },
  {
    source: "/reference/clients/js/update",
    destination: "/reference/clients/js/querybuilder#update",
    permanent: false,
  },
  {
    source: "/reference/clients/js/with",
    destination: "/reference/clients/js/querybuilder#with-blocks",
    permanent: false,
  },
  {
    source: "/reference/clients/js/reference",
    destination: "/reference/clients/js/client#client-reference",
    permanent: false,
  },
  {
    source: "/reference/reference/connection",
    destination: "/reference/connection",
    permanent: false,
  },
  {
    source: "/reference/reference/dsn",
    destination: "/reference/connection#dsn",
    permanent: false,
  },
  {
    source: "/reference/clients/python/api/asyncio_client",
    destination: "/reference/clients/python/client#asyncio-client",
    permanent: false,
  },
  {
    source: "/reference/clients/python/api/blocking_client",
    destination: "/reference/clients/python/client#blocking-client",
    permanent: false,
  },
  {
    source: "/reference/clients/python/installation",
    destination: "/reference/clients/python#installation",
    permanent: false,
  },
  {
    source: "/reference/clients/python/usage",
    destination: "/reference/clients/python#basic-usage",
    permanent: false,
  },
  {
    source: "/reference/clients/:path*",
    destination: "/reference/using/clients/:path*",
    permanent: false,
  },
  {
    source: "/reference/clients",
    destination: "/reference/using/clients",
    permanent: false,
  },
  {
    source: "/reference/connection",
    destination: "/reference/using/connection",
    permanent: false,
  },
];
