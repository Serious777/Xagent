import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Xagent',
  description: 'AI Agent with Skill System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50">{children}</body>
    </html>
  );
}
