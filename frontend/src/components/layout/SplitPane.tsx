'use client';

import { Panel, Group, Separator } from 'react-resizable-panels';
import { useUIStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';
import { GripVertical } from 'lucide-react';

interface SplitPaneProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  className?: string;
}

export function SplitPane({ leftPanel, rightPanel, className }: SplitPaneProps) {
  const { panelSizes, setPanelSizes } = useUIStore();

  return (
    <Group
      orientation="horizontal"
      onLayoutChanged={(layout) => {
        const sizes = Object.values(layout);
        if (sizes.length >= 2) {
          setPanelSizes(sizes);
        }
      }}
      className={cn('h-full flex', className)}
    >
      <Panel
        id="left"
        defaultSize={panelSizes[0] ?? 50}
        minSize={30}
        className="h-full"
      >
        <div className="h-full overflow-hidden">{leftPanel}</div>
      </Panel>

      <Separator
        className={cn(
          'w-2 bg-border hover:bg-primary/20 transition-colors',
          'flex items-center justify-center cursor-col-resize',
          'group'
        )}
      >
        <div className="flex flex-col items-center justify-center h-8 opacity-50 group-hover:opacity-100 transition-opacity">
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </div>
      </Separator>

      <Panel
        id="right"
        defaultSize={panelSizes[1] ?? 50}
        minSize={25}
        className="h-full"
      >
        <div className="h-full overflow-hidden">{rightPanel}</div>
      </Panel>
    </Group>
  );
}
