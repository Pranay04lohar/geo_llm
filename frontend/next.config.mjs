/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable webpack 5 with better file watching
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Enable hot reload debugging with polling
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: /node_modules/,
      };
    }
    return config;
  },
  
  // Enable experimental features for better development
  experimental: {
    optimizeCss: false,
  },
};

export default nextConfig;
