import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/components/providers/AuthProvider'
import { ThemeApplier } from '@/components/providers/ThemeApplier'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Intranet',
  description: 'Enterprise-grade AI-powered intranet platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeApplier />
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}

