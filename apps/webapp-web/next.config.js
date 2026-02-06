/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    images: {
        domains: ['api.ironhub.motiona.xyz', 'api.qrserver.com'],
    },
};

module.exports = nextConfig;
