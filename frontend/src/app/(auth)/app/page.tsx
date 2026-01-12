'use client';

import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout';
import { EditorPanel } from '@/components/editor/EditorPanel';
import { ChatContainer } from '@/components/chat/ChatContainer';

export default function WorkspacePage() {
  return (
    <WorkspaceLayout
      editor={<EditorPanel />}
      chat={<ChatContainer />}
    />
  );
}
