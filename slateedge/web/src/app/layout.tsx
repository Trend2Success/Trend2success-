import type { Metadata } from 'next';
import './globals.css';
import { TooltipProvider } from '@/components/ui/tooltip';

export const metadata: Metadata = {
  title: 'SlateEdge — DFS Decision Support',
  description:
    'SlateEdge is an independent, personal-use DraftKings NFL DFS decision-support and lineup-construction tool. Not affiliated with DraftKings.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-graphite-950 font-sans text-ink-50 antialiased">
        <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
      </body>
    </html>
  );
}
