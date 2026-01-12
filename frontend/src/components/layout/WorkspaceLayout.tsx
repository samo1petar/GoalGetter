'use client';

import { useState } from 'react';
import { SplitPane } from './SplitPane';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, MessageCircle } from 'lucide-react';
import { useMediaQuery } from '@/hooks/useMediaQuery';

interface WorkspaceLayoutProps {
  editor: React.ReactNode;
  chat: React.ReactNode;
}

export function WorkspaceLayout({ editor, chat }: WorkspaceLayoutProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const [activeTab, setActiveTab] = useState<'editor' | 'chat'>('editor');

  if (isDesktop) {
    return <SplitPane leftPanel={editor} rightPanel={chat} />;
  }

  // Mobile/Tablet: Tabbed interface
  return (
    <Tabs
      value={activeTab}
      onValueChange={(v) => setActiveTab(v as 'editor' | 'chat')}
      className="h-full flex flex-col"
    >
      <TabsList className="grid w-full grid-cols-2 rounded-none border-b">
        <TabsTrigger value="editor" className="flex items-center gap-2 rounded-none">
          <FileText className="w-4 h-4" />
          <span>Goals</span>
        </TabsTrigger>
        <TabsTrigger value="chat" className="flex items-center gap-2 rounded-none">
          <MessageCircle className="w-4 h-4" />
          <span>Coach</span>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="editor" className="flex-1 overflow-hidden mt-0">
        {editor}
      </TabsContent>

      <TabsContent value="chat" className="flex-1 overflow-hidden mt-0">
        {chat}
      </TabsContent>
    </Tabs>
  );
}
