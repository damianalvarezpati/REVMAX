'use client';

import { Hotel } from '@/lib/mock-data';
import { ChevronDown, Building2 } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

interface HotelSelectorProps {
  hotels: Hotel[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function HotelSelector({ hotels, selectedId, onSelect }: HotelSelectorProps) {
  const selected = hotels.find(h => h.id === selectedId);

  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-muted-foreground mb-1">Analyzing</p>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-auto p-0 hover:bg-transparent">
              <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
                <Building2 className="h-6 w-6 text-primary" />
                {selected?.name || 'Select Hotel'}
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              </h1>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-80">
            {hotels.map((hotel) => (
              <DropdownMenuItem
                key={hotel.id}
                onClick={() => onSelect(hotel.id)}
                className="flex flex-col items-start py-3"
              >
                <span className="font-medium">{hotel.name}</span>
                <span className="text-sm text-muted-foreground">
                  {hotel.city} · {hotel.category}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <p className="text-sm text-muted-foreground mt-1">
          {selected?.city}, {selected?.neighborhood}
        </p>
      </div>
    </div>
  );
}
