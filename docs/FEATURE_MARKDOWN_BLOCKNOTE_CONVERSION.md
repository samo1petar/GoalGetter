# Feature Request: Markdown ↔ BlockNote Conversion for AI Coach

## Summary

Enable bidirectional conversion between Markdown (used by AI Coach) and BlockNote JSON (used by goal editor) so that:
1. AI Coach can write formatted content that displays correctly in the Notion-style editor
2. AI Coach can read goal content as Markdown instead of plain text or raw JSON

## Current State

### Editor
- **Library**: BlockNote v0.46.1
- **Storage format**: BlockNote JSON (`PartialBlock[]` serialized to string)
- **Location**: `frontend/src/components/editor/GoalEditor.tsx`

### AI Coach ↔ Goal Data Flow

| Direction | Current Format | Problem |
|-----------|---------------|---------|
| AI reads goals | Plain text (via `parseBlockNoteContent`) | Loses formatting context (headers, lists, bold, etc.) |
| AI writes goals | Plain text | Displays as single paragraph, no formatting |

### Current Conversion Utility

```typescript
// frontend/src/hooks/useDraftGoals.ts
parseBlockNoteContent(blocks: unknown[]): string
// Converts BlockNote JSON → plain text (loses formatting)
```

## Problem

### When AI Coach Writes to Goal Editor

AI Coach generates Markdown like:
```markdown
## My Goal
**Objective**: Learn TypeScript

### Milestones
1. Complete tutorial
2. Build project
```

But the editor displays it as plain text:
```
## My Goal **Objective**: Learn TypeScript ### Milestones 1. Complete tutorial 2. Build project
```

### When AI Coach Reads from Goal Editor

User creates formatted content in BlockNote:
- Headings
- Bullet lists
- Bold/italic text

But AI Coach only sees plain text, losing the structural context.

## Proposed Solution

### BlockNote Built-in Converters

BlockNote v0.46+ includes conversion utilities in `@blocknote/core`:

```typescript
// Markdown → BlockNote Blocks
import { tryParseMarkdownToBlocks } from "@blocknote/core";
const blocks = await tryParseMarkdownToBlocks(markdownString, editor.schema);

// BlockNote Blocks → Markdown
import { blocksToMarkdownLossy } from "@blocknote/core";
const markdown = await blocksToMarkdownLossy(editor.schema, blocks);
```

**No additional packages needed** - these are included in the existing `@blocknote/core` dependency.

## Implementation Plan

### 1. Create Conversion Utility Module

**File**: `frontend/src/utils/blockNoteMarkdown.ts`

```typescript
import { BlockNoteEditor, PartialBlock } from "@blocknote/core";
import { tryParseMarkdownToBlocks, blocksToMarkdownLossy } from "@blocknote/core";

/**
 * Convert Markdown string to BlockNote blocks
 * Used when AI Coach writes goal content
 */
export async function markdownToBlocks(
  markdown: string,
  editor: BlockNoteEditor
): Promise<PartialBlock[]> {
  return await tryParseMarkdownToBlocks(markdown, editor.schema);
}

/**
 * Convert BlockNote blocks to Markdown string
 * Used when AI Coach reads goal content
 */
export async function blocksToMarkdown(
  blocks: PartialBlock[],
  editor: BlockNoteEditor
): Promise<string> {
  return await blocksToMarkdownLossy(editor.schema, blocks);
}

/**
 * Parse stored content (JSON string) to Markdown
 * For sending to AI Coach
 */
export async function goalContentToMarkdown(
  content: string,
  editor: BlockNoteEditor
): Promise<string> {
  try {
    const blocks = JSON.parse(content) as PartialBlock[];
    return await blocksToMarkdown(blocks, editor);
  } catch {
    // Content is already plain text
    return content;
  }
}
```

### 2. Update AI Coach Goal Reading

**File**: `frontend/src/hooks/useDraftGoals.ts`

Replace `parseBlockNoteContent` usage with `blocksToMarkdown` for richer context:

```typescript
// Before: Plain text extraction
const content = parseBlockNoteContent(blocks);

// After: Markdown extraction (preserves formatting)
const content = await blocksToMarkdown(blocks, editor);
```

### 3. Update AI Coach Goal Writing

**File**: `frontend/src/components/editor/GoalEditor.tsx`

When receiving content from AI Coach (via tool call), convert Markdown to blocks:

```typescript
// When AI updates goal content
async function handleAIContentUpdate(markdownContent: string) {
  const blocks = await markdownToBlocks(markdownContent, editor);
  editor.replaceBlocks(editor.document, blocks);
}
```

### 4. Update Backend Goal Tool Handler

**File**: `backend/app/services/tools/goal_tool_handler.py`

Add a flag or detection to indicate content format:

```python
# Tool input could include format hint
tool_input = {
    "content": "## Goal\n**Description**...",
    "content_format": "markdown"  # or "blocknote_json"
}
```

### 5. Update WebSocket Message Handling

When sending draft goals to backend, include Markdown version:

```typescript
// ChatContainer.tsx
const draftGoals = await Promise.all(
  getDraftsArray().map(async (draft) => ({
    ...draft,
    content_markdown: await goalContentToMarkdown(draft.content, editor)
  }))
);
```

## Supported Markdown Elements

BlockNote's converter supports:

| Markdown | BlockNote Block Type |
|----------|---------------------|
| `# Heading` | heading (level 1) |
| `## Heading` | heading (level 2) |
| `### Heading` | heading (level 3) |
| `**bold**` | text with bold style |
| `*italic*` | text with italic style |
| `- item` | bulletListItem |
| `1. item` | numberedListItem |
| `> quote` | paragraph (limited support) |
| `` `code` `` | text with code style |
| `[link](url)` | link |

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/utils/blockNoteMarkdown.ts` | **NEW** - Conversion utilities |
| `frontend/src/hooks/useDraftGoals.ts` | Use Markdown conversion for AI context |
| `frontend/src/components/editor/GoalEditor.tsx` | Handle Markdown input from AI |
| `frontend/src/containers/ChatContainer.tsx` | Send Markdown to backend |
| `backend/app/services/tools/goal_tool_handler.py` | Handle content format flag |

## Acceptance Criteria

- [ ] AI Coach written content displays with proper formatting in editor (headings, lists, bold)
- [ ] AI Coach reads goal content as Markdown with preserved structure
- [ ] Existing plain text content still works (backward compatible)
- [ ] No additional npm packages required (uses BlockNote built-ins)
- [ ] Conversion errors handled gracefully with fallback to plain text

## Edge Cases

1. **Mixed content**: Editor has some formatted blocks, some plain text
2. **Unsupported Markdown**: Features BlockNote doesn't support (tables, code blocks with language)
3. **Empty content**: Handle null/undefined gracefully
4. **Large content**: Performance for goals with many blocks

## Testing

1. AI Coach creates a goal with headers and lists → displays formatted in editor
2. User edits formatted goal → AI Coach sees Markdown structure
3. Plain text goal → still works as before
4. Rapid edits → no race conditions in conversion

## Priority

High - Core AI Coach usability improvement

## Labels

`feature`, `ai-coach`, `editor`, `blocknote`, `markdown`
