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
];
