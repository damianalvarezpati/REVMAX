'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import { hotels, analysisResults } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { 
  Building2, 
  Globe, 
  Mail, 
  MapPin, 
  Star,
  ArrowLeft,
  ExternalLink,
  Plus,
  X,
  Tag,
  Settings2,
  Link2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import Link from 'next/link';

const typeConfig = {
  primary: { label: 'Primary', className: 'bg-blue-100 text-blue-700 border-blue-200' },
  aspirational: { label: 'Aspirational', className: 'bg-purple-100 text-purple-700 border-purple-200' },
  surveillance: { label: 'Surveillance', className: 'bg-gray-100 text-gray-700 border-gray-200' },
};

export default function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const hotel = hotels.find(h => h.id === id);
  const analysis = analysisResults[id];
  const [confidenceThreshold, setConfidenceThreshold] = useState(60);
  const [defaultMode, setDefaultMode] = useState<'standard' | 'demo'>('standard');

  if (!hotel) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Hotel not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{hotel.name}</h1>
          <p className="text-muted-foreground mt-1">{hotel.city}, {hotel.neighborhood}</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Hotel Profile */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center gap-2 mb-6">
            <Building2 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Hotel Profile</h2>
          </div>

          <div className="space-y-4">
            <InfoRow icon={Building2} label="Hotel Name" value={hotel.name} />
            <InfoRow icon={MapPin} label="City" value={hotel.city} />
            <InfoRow icon={MapPin} label="Neighborhood" value={hotel.neighborhood} />
            <InfoRow icon={Star} label="Category" value={hotel.category} />
            <InfoRow icon={Building2} label="Target Room Type" value={hotel.targetRoomType} />
            <InfoRow 
              icon={Globe} 
              label="Official Website" 
              value={
                <a 
                  href={hotel.officialWebsite} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-primary hover:underline flex items-center gap-1"
                >
                  Visit site <ExternalLink className="h-3 w-3" />
                </a>
              } 
            />
            <InfoRow icon={Mail} label="Client Email" value={hotel.clientEmail} />
          </div>
        </div>

        {/* Pricing Sources */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center gap-2 mb-6">
            <Link2 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Pricing Sources</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground">Official Website URL</label>
              <Input 
                value={hotel.officialWebsite} 
                readOnly 
                className="mt-1.5"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">OTA References</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels'].map((ota) => (
                  <span
                    key={ota}
                    className="inline-flex items-center rounded-lg bg-secondary px-3 py-1.5 text-sm"
                  >
                    {ota}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Preferred Source</label>
              <div className="mt-2 p-3 rounded-xl bg-primary/5 border border-primary/10">
                <span className="text-sm font-medium">Official Website</span>
              </div>
            </div>
          </div>
        </div>

        {/* Comp Set Editor */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">Competitive Set</h2>
            </div>
            <Button variant="outline" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add
            </Button>
          </div>

          {analysis?.compSet ? (
            <div className="space-y-3">
              {analysis.compSet.map((competitor) => (
                <div
                  key={competitor.id}
                  className="group flex items-center justify-between p-4 rounded-xl bg-secondary/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-background flex items-center justify-center">
                      <Building2 className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{competitor.name}</p>
                      <span className={cn(
                        'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium border mt-1',
                        typeConfig[competitor.type].className
                      )}>
                        <Tag className="h-3 w-3" />
                        {typeConfig[competitor.type].label}
                      </span>
                    </div>
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No competitors configured
            </p>
          )}
        </div>

        {/* Analysis Preferences */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center gap-2 mb-6">
            <Settings2 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Analysis Preferences</h2>
          </div>

          <div className="space-y-6">
            <div>
              <label className="text-sm text-muted-foreground">Default Mode</label>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => setDefaultMode('standard')}
                  className={cn(
                    'flex-1 px-4 py-2.5 rounded-xl text-sm font-medium transition-all',
                    defaultMode === 'standard'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  )}
                >
                  Standard
                </button>
                <button
                  onClick={() => setDefaultMode('demo')}
                  className={cn(
                    'flex-1 px-4 py-2.5 rounded-xl text-sm font-medium transition-all',
                    defaultMode === 'demo'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  )}
                >
                  Demo
                </button>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-muted-foreground">Confidence Threshold</label>
                <span className="text-sm font-medium">{confidenceThreshold}%</span>
              </div>
              <input
                type="range"
                min="40"
                max="90"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full h-2 rounded-full appearance-none bg-secondary cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>40%</span>
                <span>90%</span>
              </div>
            </div>

            <div>
              <label className="text-sm text-muted-foreground">Preferred Channels</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels', 'Official'].map((channel) => (
                  <label
                    key={channel}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-secondary cursor-pointer hover:bg-secondary/80 transition-colors"
                  >
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">{channel}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm text-muted-foreground">Notes</label>
              <textarea
                className="mt-2 w-full rounded-xl border border-border bg-background px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                rows={3}
                placeholder="Add notes about this client..."
                defaultValue="Focus on weekend rates during high season. Contact prefers email updates."
              />
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-border">
            <Button className="w-full">Save Preferences</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface InfoRowProps {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}

function InfoRow({ icon: Icon, label, value }: InfoRowProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
