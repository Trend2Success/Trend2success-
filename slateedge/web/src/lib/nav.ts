import {
  LayoutDashboard,
  Upload,
  Users,
  FlaskConical,
  Percent,
  ListChecks,
  FolderKanban,
  Dice5,
  History,
  Settings,
  Compass,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  shortLabel?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/slates', label: 'Slate Data Import', shortLabel: 'Import', icon: Upload },
  { href: '/players', label: 'Player Pool', shortLabel: 'Players', icon: Users },
  { href: '/projections', label: 'Projection Lab', shortLabel: 'Projections', icon: FlaskConical },
  { href: '/ownership', label: 'Ownership & Leverage', shortLabel: 'Ownership', icon: Percent },
  { href: '/lineups', label: 'Lineup Builder', shortLabel: 'Lineups', icon: ListChecks },
  { href: '/portfolio', label: 'Portfolio Review', shortLabel: 'Portfolio', icon: FolderKanban },
  { href: '/simulation', label: 'Simulation Lab', shortLabel: 'Simulate', icon: Dice5 },
  { href: '/results', label: 'Contest & Results Tracker', shortLabel: 'Results', icon: History },
  { href: '/settings', label: 'Settings & Responsible Play', shortLabel: 'Settings', icon: Settings },
];

export const ONBOARDING_ITEM: NavItem = { href: '/onboarding', label: 'Onboarding', icon: Compass };
