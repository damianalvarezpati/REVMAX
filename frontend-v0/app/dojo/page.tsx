'use client';

import { useState } from 'react';
import { trainingCases, adjustmentDecisions } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { 
  Swords, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  ThumbsUp,
  ThumbsDown,
  Star,
  Building2,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  MessageSquare,
  Settings2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const recommendationConfig = {
  raise: { 
    label: 'Raise', 
    icon: TrendingUp, 
    className: 'bg-emerald-100 text-emerald-700 border-emerald-200' 
  },
  hold: { 
    label: 'Hold', 
    icon: Minus, 
    className: 'bg-blue-100 text-blue-700 border-blue-200' 
  },
  lower: { 
    label: 'Lower', 
    icon: TrendingDown, 
    className: 'bg-amber-100 text-amber-700 border-amber-200' 
  },
};

const demandConfig = {
  low: { label: 'Low', className: 'bg-red-100 text-red-700' },
  moderate: { label: 'Moderate', className: 'bg-amber-100 text-amber-700' },
  high: { label: 'High', className: 'bg-emerald-100 text-emerald-700' },
  'very-high': { label: 'Very High', className: 'bg-emerald-100 text-emerald-700' },
};

interface CaseReview {
  agreement: 'agree' | 'partial' | 'disagree' | null;
  score: number;
  feedback: string;
  adjustment: string;
}

export default function DojoPage() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [reviews, setReviews] = useState<Record<string, CaseReview>>({});

  const currentCase = trainingCases[currentIndex];
  const currentReview = reviews[currentCase.id] || {
    agreement: null,
    score: 0,
    feedback: '',
    adjustment: ''
  };

  const updateReview = (updates: Partial<CaseReview>) => {
    setReviews(prev => ({
      ...prev,
      [currentCase.id]: { ...currentReview, ...updates }
    }));
  };

  const config = recommendationConfig[currentCase.recommendation];
  const Icon = config.icon;

  // Calculate summary stats
  const completedReviews = Object.values(reviews).filter(r => r.agreement !== null);
  const avgScore = completedReviews.length > 0 
    ? (completedReviews.reduce((sum, r) => sum + r.score, 0) / completedReviews.length).toFixed(1)
    : '—';
  const agreementRate = completedReviews.length > 0
    ? Math.round((completedReviews.filter(r => r.agreement === 'agree').length / completedReviews.length) * 100)
    : 0;

  return (
    <div className="flex gap-6">
      {/* Main Content */}
      <div className="flex-1 max-w-3xl space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Swords className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-semibold tracking-tight">Dojo</h1>
          </div>
          <p className="text-muted-foreground">Review and validate AI recommendations to improve model accuracy</p>
        </div>

        {/* Case Navigation */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Case {currentIndex + 1} of {trainingCases.length}
          </span>
          <Button
            variant="outline"
            onClick={() => setCurrentIndex(Math.min(trainingCases.length - 1, currentIndex + 1))}
            disabled={currentIndex === trainingCases.length - 1}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>

        {/* Case Card */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          {/* Hotel Info */}
          <div className="flex items-center gap-3 mb-6">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold">{currentCase.hotelName}</h2>
              <p className="text-sm text-muted-foreground">Training Case #{currentCase.id}</p>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Current Price</p>
              <p className="text-xl font-semibold">€{currentCase.currentPrice}</p>
            </div>
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Market Avg</p>
              <p className="text-xl font-semibold">€{currentCase.marketAverage}</p>
            </div>
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Demand</p>
              <span className={cn(
                'inline-flex items-center rounded-lg px-2 py-0.5 text-sm font-medium',
                demandConfig[currentCase.demandLevel].className
              )}>
                {demandConfig[currentCase.demandLevel].label}
              </span>
            </div>
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Confidence</p>
              <p className="text-xl font-semibold">{currentCase.confidence}%</p>
            </div>
          </div>

          {/* Recommendation */}
          <div className={cn(
            'rounded-xl border p-4 mb-6',
            config.className
          )}>
            <div className="flex items-center gap-3">
              <Icon className="h-6 w-6" />
              <div>
                <p className="text-xs font-medium opacity-70">AI Recommendation</p>
                <p className="text-lg font-semibold capitalize">{currentCase.recommendation} Price</p>
              </div>
            </div>
          </div>

          {/* Reasoning */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm font-medium">AI Reasoning</p>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {currentCase.reasoning}
            </p>
          </div>

          {/* Review Controls */}
          <div className="space-y-6 pt-6 border-t border-border">
            {/* Agreement */}
            <div>
              <p className="text-sm font-medium mb-3">Do you agree with this recommendation?</p>
              <div className="flex gap-2">
                {([
                  { value: 'agree', label: 'Agree', icon: ThumbsUp, className: 'hover:bg-emerald-50 hover:border-emerald-200 hover:text-emerald-700' },
                  { value: 'partial', label: 'Partial', icon: Minus, className: 'hover:bg-amber-50 hover:border-amber-200 hover:text-amber-700' },
                  { value: 'disagree', label: 'Disagree', icon: ThumbsDown, className: 'hover:bg-red-50 hover:border-red-200 hover:text-red-700' },
                ] as const).map((option) => {
                  const OptionIcon = option.icon;
                  const isSelected = currentReview.agreement === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => updateReview({ agreement: option.value })}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border transition-all',
                        isSelected 
                          ? option.value === 'agree' 
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                            : option.value === 'partial'
                            ? 'bg-amber-50 border-amber-200 text-amber-700'
                            : 'bg-red-50 border-red-200 text-red-700'
                          : 'bg-secondary/50 border-transparent',
                        option.className
                      )}
                    >
                      <OptionIcon className="h-4 w-4" />
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Score */}
            <div>
              <p className="text-sm font-medium mb-3">Quality Score (1-5)</p>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    onClick={() => updateReview({ score })}
                    className={cn(
                      'flex items-center justify-center w-12 h-12 rounded-xl border transition-all',
                      currentReview.score === score
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'bg-secondary/50 border-transparent hover:bg-secondary'
                    )}
                  >
                    <Star className={cn(
                      'h-5 w-5',
                      currentReview.score >= score ? 'fill-current' : ''
                    )} />
                  </button>
                ))}
              </div>
            </div>

            {/* Feedback */}
            <div>
              <p className="text-sm font-medium mb-3">Feedback</p>
              <Textarea
                placeholder="Add your feedback or notes about this case..."
                value={currentReview.feedback}
                onChange={(e) => updateReview({ feedback: e.target.value })}
                rows={3}
              />
            </div>

            {/* Adjustment Decision */}
            <div>
              <p className="text-sm font-medium mb-3">Recommended Adjustment</p>
              <Select
                value={currentReview.adjustment}
                onValueChange={(value) => updateReview({ adjustment: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select adjustment type..." />
                </SelectTrigger>
                <SelectContent>
                  {adjustmentDecisions.map((decision) => (
                    <SelectItem key={decision.value} value={decision.value}>
                      {decision.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Submit */}
            <Button className="w-full" disabled={!currentReview.agreement}>
              Submit Review
            </Button>
          </div>
        </div>
      </div>

      {/* Summary Panel */}
      <div className="w-72 shrink-0">
        <div className="rounded-2xl bg-card p-5 shadow-sm border border-border/50 sticky top-8">
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Session Summary</h3>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Reviewed</p>
              <p className="text-2xl font-semibold">{completedReviews.length} / {trainingCases.length}</p>
            </div>
            
            <div className="p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Average Score</p>
              <p className="text-2xl font-semibold">{avgScore}</p>
            </div>
            
            <div className="p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Agreement Rate</p>
              <p className="text-2xl font-semibold">{agreementRate}%</p>
            </div>

            {completedReviews.length > 0 && (
              <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                <div className="flex items-center gap-2 mb-2">
                  <Settings2 className="h-4 w-4 text-primary" />
                  <p className="text-xs font-medium">Recommended Action</p>
                </div>
                <p className="text-sm text-muted-foreground">
                  {agreementRate >= 80 
                    ? 'Model performing well. No immediate changes needed.'
                    : agreementRate >= 60
                    ? 'Consider reviewing threshold settings.'
                    : 'Significant review of model rules recommended.'
                  }
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
