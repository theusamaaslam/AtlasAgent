import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@nous-research/ui/ui/components/button";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@nous-research/ui/ui/components/dialog";

/* ------------------------------------------------------------------ */
/*  SkillEditorDialog — create or edit a SKILL.md from the dashboard   */
/*                                                                      */
/*  Headless/VPS users have no editor besides this: the only other way */
/*  to author a custom skill is SSH + a terminal editor. Create mode   */
/*  posts a brand-new skill (name + optional category + SKILL.md);     */
/*  edit mode loads the existing SKILL.md raw text and rewrites it.    */
/*  Validation (frontmatter, name, size) happens server-side via the   */
/*  same path the agent's skill_manage tool uses, so errors come back  */
/*  as actionable messages rendered inline.                            */
/* ------------------------------------------------------------------ */

const CREATE_TEMPLATE = `---
name: my-skill
description: One-line description of when to use this skill.
---

# My Skill

Numbered steps, exact commands, and pitfalls go here.
`;

export interface SkillEditorDialogProps {
  open: boolean;
  /** Skill name to edit, or null for create mode. */
  editName: string | null;
  /** Profile to scope reads/writes to ("" = the dashboard's own profile). */
  profile?: string;
  onClose: () => void;
  /** Called after a successful save so the page can refresh its list. */
  onSaved: (name: string) => void;
}

export function SkillEditorDialog({
  open,
  editName,
  profile,
  onClose,
  onSaved,
}: SkillEditorDialogProps) {
  // The body is remounted via `key` every time the dialog opens or the
  // target skill changes, so all form state initializes through useState
  // initializers — no reset-on-open effect (react-hooks/set-state-in-effect).
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="!max-h-[calc(100dvh-2rem)] max-w-[min(68rem,calc(100vw-2rem))] rounded-2xl border-[#dfe2f1] bg-white p-6 text-[#1f1b2d] shadow-[0_28px_90px_rgba(31,27,45,0.22)]">
        {open && (
          <EditorBody
            key={editName ?? "__create__"}
            editName={editName}
            profile={profile}
            onClose={onClose}
            onSaved={onSaved}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function EditorBody({
  editName,
  profile,
  onClose,
  onSaved,
}: Omit<SkillEditorDialogProps, "open">) {
  const isEdit = editName !== null;
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [content, setContent] = useState(isEdit ? "" : CREATE_TEMPLATE);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editName) return;
    let cancelled = false;
    api
      .getSkillContent(editName, profile || undefined)
      .then((res) => !cancelled && setContent(res.content))
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [editName, profile]);

  const handleSave = async () => {
    setError(null);
    if (!isEdit && !name.trim()) {
      setError("Skill name is required.");
      return;
    }
    if (!content.trim()) {
      setError("SKILL.md content is required.");
      return;
    }
    setSaving(true);
    try {
      if (isEdit) {
        await api.updateSkillContent(editName, content, profile || undefined);
        onSaved(editName);
      } else {
        const trimmed = name.trim();
        await api.createSkill(
          {
            name: trimmed,
            content,
            category: category.trim() || undefined,
          },
          profile || undefined,
        );
        onSaved(trimmed);
      }
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <DialogHeader className="pr-8">
        <DialogTitle className="text-2xl font-semibold tracking-[0.08em] text-[#1f1b2d]">
          {isEdit ? `Edit skill: ${editName}` : "New skill"}
        </DialogTitle>
        <DialogDescription className="max-w-4xl text-sm leading-6 text-[#6b6f92]">
          {isEdit
            ? "Rewrite this skill's SKILL.md. Frontmatter (name, description) is validated on save."
            : "Author a custom skill — YAML frontmatter plus markdown instructions. It becomes available to the agent and attachable to cron jobs."}
        </DialogDescription>
      </DialogHeader>

      <div className="grid min-h-0 gap-4">
        {!isEdit && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label htmlFor="skill-editor-name">Name</Label>
              <Input
                id="skill-editor-name"
                autoFocus
                placeholder="my-skill"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="skill-editor-category">Category (optional)</Label>
              <Input
                id="skill-editor-category"
                placeholder="devops"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            </div>
          </div>
        )}

        <div className="grid gap-1.5">
          <Label htmlFor="skill-editor-content">SKILL.md</Label>
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="text-xl text-primary" />
            </div>
          ) : (
            <textarea
              id="skill-editor-content"
              spellCheck={false}
              className="min-h-[320px] max-h-[48vh] w-full resize-y rounded-xl border border-[#dfe2f1] bg-[#f7f8ff] px-4 py-3 font-mono text-sm leading-relaxed text-[#1f1b2d] shadow-inner placeholder:text-[#9aa0d7] focus-visible:border-[#8f95dc] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8f95dc]/25"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          )}
        </div>

        {error && (
          <p className="whitespace-pre-wrap text-xs text-destructive">
            {error}
          </p>
        )}

        <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center justify-end gap-2 border-t border-[#dfe2f1] bg-white/95 px-6 py-4 backdrop-blur">
          <Button ghost size="sm" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="uppercase"
            onClick={handleSave}
            disabled={saving || loading}
            prefix={saving ? <Spinner /> : undefined}
          >
            {saving ? "Saving…" : isEdit ? "Save changes" : "Create skill"}
          </Button>
        </div>
      </div>
    </>
  );
}
