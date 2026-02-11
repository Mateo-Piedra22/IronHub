/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    outputFileTracingRoot: path.join(__dirname, '../../'),
    images: {
        domains: ['ironhub.motiona.xyz', 'api.ironhub.motiona.xyz'],
    },
    async headers() {
        return [
            {
                source: '/(.*)',
                headers: [
                    { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
                    { key: 'X-Content-Type-Options', value: 'nosniff' },
                    { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
                ],
            },
        ];
    },
};

module.exports = nextConfig;
