'use client';

import { useState } from 'react';
import { hotels, analysisResults } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { 
  Building2, 
  MapPin, 
  Clock, 
  ChevronRight,
  Plus,
  Search,
  Filter
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import Link from 'next/link';

const statusConfig = {
  active: { label: 'Active', className: 'bg-emerald-100 text-emerald-700' },
  inactive: { label: 'Inactive', className: 'bg-gray-100 text-gray-700' },
  pending: { label: 'Pending', className: 'bg-amber-100 text-amber-700' },
};

const planConfig = {
  starter: { label: 'Starter', className: 'bg-gray-100 text-gray-700' },
  professional: { label: 'Professional', className: 'bg-blue-100 text-blue-700' },
  enterprise: { label: 'Enterprise', className: 'bg-purple-100 text-purple-700' },
};

export default function ClientsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const filteredHotels = hotels.filter(hotel => {
    const matchesSearch = hotel.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      hotel.city.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = !statusFilter || hotel.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clients</h1>
          <p className="text-muted-foreground mt-1">Manage your hotel clients and their configurations</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Client
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search hotels..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex gap-1">
            {['active', 'inactive', 'pending'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(statusFilter === status ? null : status)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize',
                  statusFilter === status
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                )}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Client Cards */}
      <div className="grid gap-4">
        {filteredHotels.map((hotel) => {
          const analysis = analysisResults[hotel.id];
          return (
            <Link
              key={hotel.id}
              href={`/clients/${hotel.id}`}
              className="group flex items-center justify-between p-6 rounded-2xl bg-card shadow-sm border border-border/50 hover:shadow-md hover:border-primary/20 transition-all duration-300"
            >
              <div className="flex items-center gap-5">
                <div className="h-14 w-14 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Building2 className="h-7 w-7 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold group-hover:text-primary transition-colors">
                    {hotel.name}
                  </h3>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <MapPin className="h-4 w-4" />
                      {hotel.city}
                    </span>
                    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      {hotel.lastAnalysis}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex flex-col items-end gap-2">
                  <div className="flex gap-2">
                    <span className={cn(
                      'inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium',
                      statusConfig[hotel.status].className
                    )}>
                      {statusConfig[hotel.status].label}
                    </span>
                    <span className={cn(
                      'inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium',
                      planConfig[hotel.plan].className
                    )}>
                      {planConfig[hotel.plan].label}
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {hotel.currentStrategy}
                  </span>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
            </Link>
          );
        })}
      </div>

      {filteredHotels.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <Building2 className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground">No hotels found matching your criteria</p>
        </div>
      )}
    </div>
  );
}
