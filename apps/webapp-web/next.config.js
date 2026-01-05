/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    images: {
        domains: ['api.ironhub.motiona.xyz'],
    },
};

module.exports = nextConfig;
