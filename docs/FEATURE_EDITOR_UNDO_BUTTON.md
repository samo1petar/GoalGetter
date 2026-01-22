# Feature: Add Undo/Redo Buttons to Editor

## Overview
Add Undo and Redo buttons to the editor toolbar so users can undo changes, especially when the AI Coach makes undesirable edits to their goals.

## Current State
- Editor uses BlockNote v0.46.1 (has built-in undo/redo)
- Toolbar is in EditorPanel.tsx
- Editor instance is created in GoalEditor.tsx but NOT exposed to parent
- Ctrl+Z works (handled by BlockNote) but no visible buttons

---

## Implementation Tasks

### Task 1: Expose Editor Instance from GoalEditor

**File:** `frontend/src/components/editor/GoalEditor.tsx`

1. Add import for BlockNoteEditor type at the top:
```typescript
import type { BlockNoteEditor } from '@blocknote/core';
```

2. Update the GoalEditorProps interface to add the callback:
```typescript
interface GoalEditorProps {
  initialContent?: string;
  onContentChange?: (content: string, markdown: string) => void;
  goalId?: string;
  contentFormat?: 'markdown' | 'blocknote_json';
  onEditorReady?: (editor: BlockNoteEditor) => void;
}
```

3. Add a useEffect after the editor is created to call the callback:
```typescript
// Add after the useCreateBlockNote hook (around line 71)
useEffect(() => {
  if (editor && onEditorReady) {
    onEditorReady(editor);
  }
}, [editor, onEditorReady]);
```

4. Destructure `onEditorReady` from props in the component.

---

### Task 2: Add Undo/Redo Buttons to EditorPanel

**File:** `frontend/src/components/editor/EditorPanel.tsx`

1. Add imports at the top:
```typescript
import { Undo2, Redo2 } from 'lucide-react';
import type { BlockNoteEditor } from '@blocknote/core';
```

2. Add state to hold the editor reference (after other useState calls):
```typescript
const [editor, setEditor] = useState<BlockNoteEditor | null>(null);
```

3. Pass the callback to GoalEditor. Find the GoalEditor component and add the prop:
```typescript
<GoalEditor
  key={goal?.id}
  initialContent={goal?.content}
  goalId={goal?.id}
  contentFormat={goal?.metadata?.content_format}
  onContentChange={handleContentChange}
  onEditorReady={setEditor}
/>
```

4. Add Undo/Redo buttons to the toolbar. Find the toolbar section (the div with `flex items-center justify-between`) and add the buttons after the phase badge, in the left section:

```typescript
{/* After the phase Badge, add: */}
{editor && (
  <div className="flex items-center gap-1 ml-2">
    <Button
      variant="ghost"
      size="icon"
      onClick={() => editor.undo()}
      title="Undo (Ctrl+Z)"
    >
      <Undo2 className="h-4 w-4" />
    </Button>
    <Button
      variant="ghost"
      size="icon"
      onClick={() => editor.redo()}
      title="Redo (Ctrl+Y)"
    >
      <Redo2 className="h-4 w-4" />
    </Button>
  </div>
)}
```

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/editor/GoalEditor.tsx` | Add `onEditorReady` prop, expose editor instance via useEffect |
| `frontend/src/components/editor/EditorPanel.tsx` | Add editor state, Undo/Redo buttons to toolbar |

---

## Verification

1. Start the frontend: `cd frontend && npm run dev`
2. Open a goal in the editor
3. Make some edits (type text, delete, etc.)
4. Click the Undo button (left-facing arrow icon)
5. **Expected:** Last change is undone
6. Click the Redo button (right-facing arrow icon)
7. **Expected:** Change is redone
8. Test with AI Coach: Ask AI to update a goal, then click Undo
9. **Expected:** AI Coach's changes are reverted
