'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { 
  Settings, 
  Sliders, 
  Bell, 
  FileText, 
  Plug, 
  Shield,
  Save,
  ChevronRight,
  Check,
  ExternalLink
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const sections = [
  { id: 'system', label: 'System Defaults', icon: Settings },
  { id: 'confidence', label: 'Confidence Thresholds', icon: Sliders },
  { id: 'analysis', label: 'Analysis Mode', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'reports', label: 'Report Style', icon: FileText },
  { id: 'integrations', label: 'Integrations', icon: Plug },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState('system');
  const [saved, setSaved] = useState(false);

  // System defaults
  const [defaultMode, setDefaultMode] = useState('standard');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState('30');

  // Confidence thresholds
  const [minConfidence, setMinConfidence] = useState(50);
  const [warningThreshold, setWarningThreshold] = useState(65);
  const [highConfidence, setHighConfidence] = useState(80);

  // Notifications
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [criticalOnly, setCriticalOnly] = useState(false);
  const [dailyDigest, setDailyDigest] = useState(true);
  const [weeklyReport, setWeeklyReport] = useState(true);

  // Report style
  const [reportFormat, setReportFormat] = useState('detailed');
  const [includeCharts, setIncludeCharts] = useState(true);
  const [includeCompset, setIncludeCompset] = useState(true);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="flex gap-8">
      {/* Sidebar Navigation */}
      <div className="w-64 shrink-0">
        <h1 className="text-2xl font-semibold tracking-tight mb-6">Settings</h1>
        <nav className="space-y-1">
          {sections.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                )}
              >
                <Icon className="h-5 w-5" />
                {section.label}
                {isActive && <ChevronRight className="h-4 w-4 ml-auto" />}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content Area */}
      <div className="flex-1 max-w-2xl">
        {/* System Defaults */}
        {activeSection === 'system' && (
          <SettingsSection title="System Defaults" description="Configure default system behavior">
            <SettingItem label="Default Analysis Mode" description="Choose the default mode for new analyses">
              <Select value={defaultMode} onValueChange={setDefaultMode}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="demo">Demo</SelectItem>
                  <SelectItem value="deep">Deep Analysis</SelectItem>
                </SelectContent>
              </Select>
            </SettingItem>

            <SettingItem label="Auto-Refresh Dashboard" description="Automatically refresh dashboard data">
              <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
            </SettingItem>

            {autoRefresh && (
              <SettingItem label="Refresh Interval" description="How often to refresh data (minutes)">
                <Select value={refreshInterval} onValueChange={setRefreshInterval}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 minutes</SelectItem>
                    <SelectItem value="30">30 minutes</SelectItem>
                    <SelectItem value="60">1 hour</SelectItem>
                  </SelectContent>
                </Select>
              </SettingItem>
            )}

            <SettingItem label="Timezone" description="Set your preferred timezone">
              <Select defaultValue="europe_berlin">
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="europe_berlin">Europe/Berlin</SelectItem>
                  <SelectItem value="europe_london">Europe/London</SelectItem>
                  <SelectItem value="america_new_york">America/New York</SelectItem>
                  <SelectItem value="asia_tokyo">Asia/Tokyo</SelectItem>
                </SelectContent>
              </Select>
            </SettingItem>
          </SettingsSection>
        )}

        {/* Confidence Thresholds */}
        {activeSection === 'confidence' && (
          <SettingsSection title="Confidence Thresholds" description="Set confidence level thresholds for recommendations">
            <SettingItem 
              label="Minimum Confidence" 
              description="Below this level, recommendations are flagged as uncertain"
            >
              <div className="w-48 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{minConfidence}%</span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="70"
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(Number(e.target.value))}
                  className="w-full h-2 rounded-full appearance-none bg-secondary cursor-pointer accent-primary"
                />
              </div>
            </SettingItem>

            <SettingItem 
              label="Warning Threshold" 
              description="Confidence levels below this trigger a warning"
            >
              <div className="w-48 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{warningThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="80"
                  value={warningThreshold}
                  onChange={(e) => setWarningThreshold(Number(e.target.value))}
                  className="w-full h-2 rounded-full appearance-none bg-secondary cursor-pointer accent-primary"
                />
              </div>
            </SettingItem>

            <SettingItem 
              label="High Confidence" 
              description="Above this level, recommendations are marked as high confidence"
            >
              <div className="w-48 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{highConfidence}%</span>
                </div>
                <input
                  type="range"
                  min="70"
                  max="95"
                  value={highConfidence}
                  onChange={(e) => setHighConfidence(Number(e.target.value))}
                  className="w-full h-2 rounded-full appearance-none bg-secondary cursor-pointer accent-primary"
                />
              </div>
            </SettingItem>
          </SettingsSection>
        )}

        {/* Analysis Mode */}
        {activeSection === 'analysis' && (
          <SettingsSection title="Analysis Mode Defaults" description="Configure default analysis behavior">
            <SettingItem label="Compset Auto-Detection" description="Automatically detect comparable hotels">
              <Switch defaultChecked />
            </SettingItem>

            <SettingItem label="Include Events Analysis" description="Analyze local events impact on demand">
              <Switch defaultChecked />
            </SettingItem>

            <SettingItem label="Parity Checking" description="Check rate parity across distribution channels">
              <Switch defaultChecked />
            </SettingItem>

            <SettingItem label="Reputation Analysis" description="Include reputation scoring in analysis">
              <Switch defaultChecked />
            </SettingItem>

            <SettingItem label="Historical Comparison" description="Compare with historical performance">
              <Switch defaultChecked={false} />
            </SettingItem>
          </SettingsSection>
        )}

        {/* Notifications */}
        {activeSection === 'notifications' && (
          <SettingsSection title="Notification Settings" description="Configure how you receive alerts and updates">
            <SettingItem label="Email Alerts" description="Receive alerts via email">
              <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} />
            </SettingItem>

            {emailAlerts && (
              <>
                <SettingItem label="Critical Alerts Only" description="Only send critical severity alerts">
                  <Switch checked={criticalOnly} onCheckedChange={setCriticalOnly} />
                </SettingItem>

                <SettingItem label="Daily Digest" description="Receive a daily summary email">
                  <Switch checked={dailyDigest} onCheckedChange={setDailyDigest} />
                </SettingItem>

                <SettingItem label="Weekly Report" description="Receive a weekly performance report">
                  <Switch checked={weeklyReport} onCheckedChange={setWeeklyReport} />
                </SettingItem>

                <SettingItem label="Email Address" description="Where to send notifications">
                  <Input 
                    type="email" 
                    placeholder="you@example.com" 
                    defaultValue="revenue@catalonia-berlin.com"
                    className="w-64"
                  />
                </SettingItem>
              </>
            )}
          </SettingsSection>
        )}

        {/* Report Style */}
        {activeSection === 'reports' && (
          <SettingsSection title="Report Style" description="Customize how reports are generated">
            <SettingItem label="Report Format" description="Choose default report detail level">
              <Select value={reportFormat} onValueChange={setReportFormat}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="summary">Summary</SelectItem>
                  <SelectItem value="detailed">Detailed</SelectItem>
                  <SelectItem value="executive">Executive Brief</SelectItem>
                </SelectContent>
              </Select>
            </SettingItem>

            <SettingItem label="Include Charts" description="Add visual charts to reports">
              <Switch checked={includeCharts} onCheckedChange={setIncludeCharts} />
            </SettingItem>

            <SettingItem label="Include Compset Details" description="Show detailed competitor information">
              <Switch checked={includeCompset} onCheckedChange={setIncludeCompset} />
            </SettingItem>

            <SettingItem label="Branding" description="Include company branding in reports">
              <Switch defaultChecked />
            </SettingItem>
          </SettingsSection>
        )}

        {/* Integrations */}
        {activeSection === 'integrations' && (
          <SettingsSection title="Integrations" description="Connect external services and data sources">
            <IntegrationItem 
              name="Booking.com" 
              description="Connect to Booking.com for rate data"
              connected
            />
            <IntegrationItem 
              name="Expedia" 
              description="Connect to Expedia for rate and availability"
              connected
            />
            <IntegrationItem 
              name="Google Hotels" 
              description="Connect to Google Hotels for visibility data"
              connected
            />
            <IntegrationItem 
              name="STR" 
              description="Connect to STR for market benchmarking"
              connected={false}
            />
            <IntegrationItem 
              name="RateGain" 
              description="Connect to RateGain for comprehensive rate shopping"
              connected={false}
            />
            <IntegrationItem 
              name="Slack" 
              description="Send notifications to Slack channels"
              connected={false}
            />
          </SettingsSection>
        )}

        {/* Save Button */}
        <div className="flex items-center justify-end gap-4 pt-6 mt-6 border-t border-border">
          <Button variant="outline">Reset to Defaults</Button>
          <Button onClick={handleSave}>
            {saved ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Saved
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface SettingsSectionProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

function SettingsSection({ title, description, children }: SettingsSectionProps) {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
      </div>
      <div className="space-y-6">
        {children}
      </div>
    </div>
  );
}

interface SettingItemProps {
  label: string;
  description: string;
  children: React.ReactNode;
}

function SettingItem({ label, description, children }: SettingItemProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-border/50 last:border-0">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {children}
    </div>
  );
}

interface IntegrationItemProps {
  name: string;
  description: string;
  connected: boolean;
}

function IntegrationItem({ name, description, connected }: IntegrationItemProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-4">
        <div className={cn(
          'h-10 w-10 rounded-xl flex items-center justify-center text-sm font-semibold',
          connected ? 'bg-emerald-100 text-emerald-700' : 'bg-secondary text-muted-foreground'
        )}>
          {name[0]}
        </div>
        <div>
          <p className="text-sm font-medium">{name}</p>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      {connected ? (
        <span className="inline-flex items-center gap-1.5 text-sm text-emerald-600">
          <Check className="h-4 w-4" />
          Connected
        </span>
      ) : (
        <Button variant="outline" size="sm">
          <Plug className="h-4 w-4 mr-2" />
          Connect
        </Button>
      )}
    </div>
  );
}
