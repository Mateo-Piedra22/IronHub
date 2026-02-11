/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
    reactStrictMode: true,
    outputFileTracingRoot: path.join(__dirname, '../../'),
    images: {
        remotePatterns: [
            { protocol: 'https', hostname: '*.ironhub.motiona.xyz' },
            { protocol: 'https', hostname: 'cdn.ironhub.motiona.xyz' },
        ],
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
