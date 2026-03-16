'use client';

import { useState } from 'react';
import { Competitor } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { Building2, Plus, X, Search, Tag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface CompSetEditorProps {
  compSet: Competitor[];
}

const typeConfig = {
  primary: { label: 'Primary', className: 'bg-blue-100 text-blue-700 border-blue-200' },
  aspirational: { label: 'Aspirational', className: 'bg-purple-100 text-purple-700 border-purple-200' },
  surveillance: { label: 'Surveillance', className: 'bg-gray-100 text-gray-700 border-gray-200' },
};

export function CompSetEditor({ compSet }: CompSetEditorProps) {
  const [competitors, setCompetitors] = useState(compSet);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddOpen, setIsAddOpen] = useState(false);

  const handleRemove = (id: string) => {
    setCompetitors(competitors.filter(c => c.id !== id));
  };

  // Mock search results
  const mockSearchResults = [
    { id: 'new1', name: 'Adlon Kempinski Berlin', type: 'aspirational' as const },
    { id: 'new2', name: 'Scandic Berlin Potsdamer Platz', type: 'primary' as const },
    { id: 'new3', name: 'ibis Styles Berlin Mitte', type: 'surveillance' as const },
  ].filter(r => 
    searchQuery && r.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
    !competitors.find(c => c.id === r.id)
  );

  const handleAdd = (competitor: Competitor) => {
    setCompetitors([...competitors, competitor]);
    setSearchQuery('');
    setIsAddOpen(false);
  };

  if (competitors.length === 0) {
    return (
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Comparable Hotels</h3>
        </div>
        <div className="text-center py-8">
          <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <Building2 className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground mb-4">
            Comparable hotels could not be detected automatically.
          </p>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Competitors Manually
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Comparable Hotels</h3>
        </div>
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Competitor
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Competitor</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search hotels..."
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              {searchQuery && (
                <div className="space-y-2">
                  {mockSearchResults.length > 0 ? (
                    mockSearchResults.map((result) => (
                      <button
                        key={result.id}
                        onClick={() => handleAdd(result)}
                        className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-secondary transition-colors text-left"
                      >
                        <div>
                          <p className="font-medium">{result.name}</p>
                          <span className={cn(
                            'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium border mt-1',
                            typeConfig[result.type].className
                          )}>
                            {typeConfig[result.type].label}
                          </span>
                        </div>
                        <Plus className="h-4 w-4 text-muted-foreground" />
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No hotels found. Try a different search.
                    </p>
                  )}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-3">
        {competitors.map((competitor) => (
          <div
            key={competitor.id}
            className="group flex items-center justify-between p-4 rounded-xl bg-secondary/50 hover:bg-secondary transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-background flex items-center justify-center">
                <Building2 className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-medium">{competitor.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn(
                    'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium border',
                    typeConfig[competitor.type].className
                  )}>
                    <Tag className="h-3 w-3" />
                    {typeConfig[competitor.type].label}
                  </span>
                  {competitor.price && (
                    <span className="text-sm text-muted-foreground">
                      €{competitor.price}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={() => handleRemove(competitor.id)}
              className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
