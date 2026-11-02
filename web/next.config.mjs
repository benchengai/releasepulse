/** Static export: the demo is plain files, deployable to Vercel or any static host.
 * DEMO_BASE_PATH serves it from a sub-path, e.g. /demos/releasepulse on a personal site. */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath: process.env.DEMO_BASE_PATH ?? "",
};

export default nextConfig;
