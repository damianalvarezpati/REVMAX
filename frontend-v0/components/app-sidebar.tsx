'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { 
  BarChart3, 
  LayoutDashboard, 
  Building2, 
  FileText, 
  Bell, 
  Swords, 
  Settings,
  Activity,
  RefreshCw
} from 'lucide-react';
import { systemStatus } from '@/lib/mock-data';

const navItems = [
  { href: '/', icon: BarChart3, label: 'Analysis' },
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/clients', icon: Building2, label: 'Clients' },
  { href: '/reports', icon: FileText, label: 'Reports' },
  { href: '/alerts', icon: Bell, label: 'Alerts', badge: 4 },
  { href: '/dojo', icon: Swords, label: 'Dojo' },
  { href: '/settings', icon: Settings, label: 'Settings' }
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="flex flex-col px-6 pt-8 pb-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sidebar-primary">
            <BarChart3 className="h-5 w-5 text-sidebar-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-white">RevMax</h1>
            <p className="text-xs text-sidebar-muted">Revenue Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== '/' && pathname.startsWith(item.href));
            const Icon = item.icon;
            
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-sidebar-accent text-white'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-white'
                  )}
                >
                  <Icon className={cn(
                    'h-5 w-5 transition-colors',
                    isActive ? 'text-sidebar-primary' : 'text-sidebar-muted group-hover:text-sidebar-foreground'
                  )} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-sidebar-primary px-1.5 text-xs font-medium text-sidebar-primary-foreground">
                      {item.badge}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-4 py-4">
        <div className="flex items-center gap-2 text-xs text-sidebar-muted">
          <Activity className="h-3.5 w-3.5" />
          <span>System {systemStatus.status}</span>
          <span className="ml-auto flex items-center gap-1">
            <RefreshCw className="h-3 w-3" />
            {systemStatus.lastSync}
          </span>
        </div>
      </div>
    </aside>
  );
}
