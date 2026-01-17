'use client';

import OwnerLayout from '@/components/layouts/OwnerLayout';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <OwnerLayout>{children}</OwnerLayout>;
}
