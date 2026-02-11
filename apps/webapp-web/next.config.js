/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
    reactStrictMode: true,
    outputFileTracingRoot: path.join(__dirname, '../../'),
    images: {
        domains: ['api.ironhub.motiona.xyz', 'api.qrserver.com'],
    },
};

module.exports = nextConfig;
