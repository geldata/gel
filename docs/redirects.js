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
    source: "/reference/reference/bindings/datetime",
    destination: "/reference/using/datetime",
    permanent: false,
  },
  {
    source: "/reference/reference/bindings",
    destination: "/reference/using",
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
    destination: "/reference/using/js/querybuilder",
    permanent: false,
  },
  {
    source: "/reference/clients/js/driver",
    destination: "/reference/using/js",
    permanent: false,
  },
  {
    source: "/reference/clients/js/for",
    destination: "/reference/using/js/querybuilder#for",
    permanent: false,
  },
  {
    source: "/reference/clients/js/funcops",
    destination: "/reference/using/js/querybuilder#functions-and-operators",
    permanent: false,
  },
  {
    source: "/reference/clients/js/group",
    destination: "/reference/using/js/querybuilder#group",
    permanent: false,
  },
  {
    source: "/reference/clients/js/insert",
    destination: "/reference/using/js/querybuilder#insert",
    permanent: false,
  },
  {
    source: "/reference/clients/js/literals",
    destination: "/reference/using/js/querybuilder#types-and-literals",
    permanent: false,
  },
  {
    source: "/reference/clients/js/objects",
    destination: "/reference/using/js/querybuilder#objects-and-paths",
    permanent: false,
  },
  {
    source: "/reference/clients/js/parameters",
    destination: "/reference/using/js/querybuilder#parameters",
    permanent: false,
  },
  {
    source: "/reference/clients/js/select",
    destination: "/reference/using/js/querybuilder#select",
    permanent: false,
  },
  {
    source: "/reference/clients/js/types",
    destination: "/reference/using/js/querybuilder#types-and-literals",
    permanent: false,
  },
  {
    source: "/reference/clients/js/update",
    destination: "/reference/using/js/querybuilder#update",
    permanent: false,
  },
  {
    source: "/reference/clients/js/with",
    destination: "/reference/using/js/querybuilder#with-blocks",
    permanent: false,
  },
  {
    source: "/reference/clients/js/reference",
    destination: "/reference/using/js/client#client-reference",
    permanent: false,
  },
  {
    source: "/reference/reference/connection",
    destination: "/reference/using/connection",
    permanent: false,
  },
  {
    source: "/reference/reference/dsn",
    destination: "/reference/using/connection#dsn",
    permanent: false,
  },
  {
    source: "/reference/clients/python/api/asyncio_client",
    destination: "/reference/using/python/client#asyncio-client",
    permanent: false,
  },
  {
    source: "/reference/clients/python/api/blocking_client",
    destination: "/reference/using/python/client#blocking-client",
    permanent: false,
  },
  {
    source: "/reference/clients/python/installation",
    destination: "/reference/using/python#installation",
    permanent: false,
  },
  {
    source: "/reference/clients/python/usage",
    destination: "/reference/using/python#basic-usage",
    permanent: false,
  },
  {
    source: "/reference/clients/http/health-checks",
    destination: "/reference/running/http#health-checks",
    permanent: false,
  },
  {
    source: "/reference/clients/http/protocol",
    destination: "/reference/using/http",
    permanent: false,
  },
  {
    source: "/reference/clients/:path*",
    destination: "/reference/using/:path*",
    permanent: false,
  },
  {
    source: "/reference/reference/configuration",
    destination: "/reference/running/configuration",
    permanent: false,
  },
  {
    source: "/reference/reference/environment",
    destination: "/reference/running/environment",
    permanent: false,
  },
  {
    source: "/reference/reference/gel_toml",
    destination: "/reference/using/projects#gel-toml",
    permanent: false,
  },
  {
    source: "/reference/reference/http",
    destination: "/reference/running/http",
    permanent: false,
  },
  {
    source: "/reference/reference/projects",
    destination: "/reference/using/projects",
    permanent: false,
  },
  {
    source: "/reference/reference/protocol/:path*",
    destination: "/resources/protocol/:path*",
    permanent: false,
  },
  {
    source: "/reference/reference/admin/databases",
    destination: "/reference/datamodel/branches",
    permanent: false,
  },
  {
    source: "/reference/reference/admin/:path*",
    destination: "/reference/running/admin/:path*",
    permanent: false,
  },
  {
    source: "/reference/reference/backend-ha",
    destination: "/reference/running/backend-ha",
    permanent: false,
  },
  {
    source: "/resources/guides/deployment/:path*",
    destination: "/reference/running/deployment/:path*",
    permanent: false,
  },
  {
    source: "/reference/reference/postgis",
    destination: "/reference/stdlib/postgis",
    permanent: true,
  },
  {
    source: "/reference/cli/:path*",
    destination: "/reference/using/cli/:path*",
    permanent: false,
  },
];
