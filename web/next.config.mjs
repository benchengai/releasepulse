/** Static export: the demo is plain files, deployable to Vercel or any static host. */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
