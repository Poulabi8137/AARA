"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  FolderPlus,
  Loader2,
  FileText,
  ListChecks,
  Search,
  Microscope,
  Lightbulb,
  PenLine,
  Check,
  Globe,
  Target,
  Users,
  LayoutDashboard,
  ChevronRight,
} from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace/workspace-layout";
import { WorkspaceHeader } from "@/components/workspace/workspace-header";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCurrentWorkspaceId,
  useCreateWorkspace,
} from "@/hooks/workspace-queries";
import { useCreateProject } from "@/hooks/project-queries";
import {
  useSubmitResearchQuery,
  useGenerateScopingSuggestion,
  useResearchRecentActivity,
} from "@/hooks/research-queries";
import { cn } from "@/lib/utils";

interface RecentActivityItem {
  id: string;
  type: "task" | "paper";
  title: string;
  timestamp: string | null;
  status: string;
  project_id: string | null;
}

interface LaunchStep {
  id: string;
  label: string;
  icon: React.ElementType;
  done: boolean;
  current: boolean;
}

const TOPIC_EXAMPLES = [
  "Few-shot learning for low-resource languages",
  "Retrieval-augmented generation for scientific QA",
  "Multi-agent coordination in autonomous systems",
  "Energy-efficient transformer architectures",
];

const PIPELINE_STEPS = [
  {
    icon: Search,
    label: "Search the literature",
    desc: "Finding relevant papers",
  },
  {
    icon: Microscope,
    label: "Analyze findings",
    desc: "Identifying patterns and gaps",
  },
  {
    icon: Lightbulb,
    label: "Generate ideas",
    desc: "Proposing novel directions",
  },
  { icon: PenLine, label: "Draft results", desc: "Synthesizing into a paper" },
];

function projectNameFromTopic(topic: string) {
  const trimmed = topic.trim();
  return trimmed.length > 60 ? `${trimmed.slice(0, 57)}…` : trimmed;
}

function RecentActivityList() {
  const { data, isLoading } = useResearchRecentActivity();
  const items = (data ?? []) as RecentActivityItem[];

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg p-3">
            <Skeleton className="size-8 shrink-0 rounded-lg" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-3/5" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-center">
        <div className="flex size-10 items-center justify-center rounded-xl bg-muted/50">
          <FileText className="size-4 text-muted-foreground/60" />
        </div>
        <p className="text-xs text-muted-foreground/70 max-w-[18rem]">
          Nothing yet — start your first research above and it will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border/40">
      {items.slice(0, 5).map((item) => {
        const Icon = item.type === "paper" ? FileText : ListChecks;
        const href = item.project_id
          ? item.type === "paper"
            ? `/projects/${item.project_id}/papers`
            : `/projects/${item.project_id}/agent-workspace`
          : null;

        const content = (
          <>
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent/50">
              <Icon className="size-3.5 text-muted-foreground/70" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground/90">
                {item.title}
              </p>
              <p className="text-xs text-muted-foreground/60">
                {item.timestamp
                  ? new Date(item.timestamp).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  : ""}
                {" · "}
                {item.type === "paper" ? "Paper" : "Research"}
              </p>
            </div>
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/30" />
          </>
        );

        const baseClass =
          "flex items-center gap-3 py-2.5 px-2 rounded-lg transition-all";
        return href ? (
          <Link
            key={item.id}
            href={href}
            className={cn(baseClass, "hover:bg-accent/40 group cursor-pointer")}
          >
            {content}
          </Link>
        ) : (
          <div key={item.id} className={baseClass}>
            {content}
          </div>
        );
      })}
    </div>
  );
}

function LaunchSequence({
  steps,
  visible,
}: {
  steps: LaunchStep[];
  visible: boolean;
}) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
          className="overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-b from-accent/50 to-card/50 p-3"
        >
          <div className="space-y-1">
            {steps.map((step, i) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08, duration: 0.3 }}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all",
                  step.current && "bg-primary/10",
                  step.done && "opacity-80",
                  !step.current && !step.done && "opacity-40",
                )}
              >
                <div
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-md transition-all",
                    step.done && "bg-aara-good/20 text-aara-good",
                    step.current && "bg-primary/20 text-primary",
                    !step.current &&
                      !step.done &&
                      "bg-muted text-muted-foreground",
                  )}
                >
                  {step.done ? (
                    <Check className="size-3.5" />
                  ) : step.current ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <step.icon className="size-3.5" />
                  )}
                </div>
                <span
                  className={cn(
                    "font-medium",
                    step.done &&
                      "text-muted-foreground line-through decoration-muted-foreground/30",
                    step.current && "text-foreground",
                    !step.current && !step.done && "text-muted-foreground/60",
                  )}
                >
                  {step.label}
                </span>
              </motion.div>
            ))}
          </div>
          <motion.div
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{ duration: 2, ease: "easeInOut" }}
            className="mt-2 h-0.5 rounded-full bg-gradient-to-r from-primary/40 via-primary to-primary/40"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function ResearchNewPage() {
  const router = useRouter();
  const currentWorkspaceId = useCurrentWorkspaceId();
  const createWorkspace = useCreateWorkspace();
  const createProject = useCreateProject();
  const submitQuery = useSubmitResearchQuery();
  const scoping = useGenerateScopingSuggestion();

  const [topic, setTopic] = useState("");
  const [researchDirection, setResearchDirection] = useState("");
  const [maxPapers, setMaxPapers] = useState(50);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [showLaunch, setShowLaunch] = useState(false);
  const [launchSteps, setLaunchSteps] = useState<LaunchStep[]>([
    {
      id: "topic",
      label: "Understanding topic...",
      icon: Globe,
      done: false,
      current: false,
    },
    {
      id: "fields",
      label: "Finding related fields...",
      icon: Search,
      done: false,
      current: false,
    },
    {
      id: "planning",
      label: "Planning research...",
      icon: Target,
      done: false,
      current: false,
    },
    {
      id: "team",
      label: "Creating AI team...",
      icon: Users,
      done: false,
      current: false,
    },
    {
      id: "workspace",
      label: "Initializing workspace...",
      icon: LayoutDashboard,
      done: false,
      current: false,
    },
  ]);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setExampleIndex((i) => (i + 1) % TOPIC_EXAMPLES.length);
    }, 3200);
    return () => clearInterval(interval);
  }, []);

  const isStarting =
    createProject.isPending || submitQuery.isPending || showLaunch;

  const handleGetSuggestions = () => {
    if (!topic.trim()) return;
    scoping.mutate({ topic: topic.trim() });
  };

  const runLaunchSequence = async (projectId: string) => {
    setShowLaunch(true);
    const stepIds = ["topic", "fields", "planning", "team", "workspace"];

    for (let i = 0; i < stepIds.length; i++) {
      await new Promise((r) => setTimeout(r, 350 + Math.random() * 250));
      setLaunchSteps((prev) =>
        prev.map((s) =>
          s.id === stepIds[i]
            ? { ...s, current: true }
            : stepIds.indexOf(s.id) < i
              ? { ...s, done: true, current: false }
              : { ...s, current: false },
        ),
      );
    }

    await new Promise((r) => setTimeout(r, 400));
    setShowLaunch(false);
    router.push(`/projects/${projectId}/agent-workspace`);
  };

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || !currentWorkspaceId) return;

    createProject.mutate(
      {
        workspace_id: currentWorkspaceId,
        name: projectNameFromTopic(topic),
        research_goal: topic.trim(),
      },
      {
        onSuccess: (project) => {
          submitQuery.mutate(
            {
              query: topic.trim(),
              project_id: project.id,
              max_papers: maxPapers,
              research_direction: researchDirection.trim() || undefined,
            },
            {
              onSuccess: () => {
                console.log(
                  "[handleStart] Query submitted, running launch sequence",
                  { projectId: project.id },
                );
                runLaunchSequence(project.id);
              },
            },
          );
        },
        onError: (error) => {
          console.error("[handleStart] Project creation failed", error);
        },
      },
    );
  };

  const handleStartFromEmpty = () => {
    if (!currentWorkspaceId) return;
    createWorkspace.mutate({ name: "My Workspace" });
  };

  const hasTopic = topic.trim().length > 0;

  return (
    <WorkspaceLayout header={<WorkspaceHeader title="New Research" />}>
      <div className="relative mx-auto max-w-2xl py-8 md:py-12">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-[-6rem] -z-10 flex justify-center overflow-hidden"
        >
          <div className="size-[36rem] rounded-full bg-gradient-to-br from-primary/[0.07] via-primary/[0.04] to-transparent blur-[120px]" />
          <div className="absolute top-1/3 size-[20rem] rounded-full bg-[#a78bfa]/[0.04] blur-[100px]" />
        </div>

        {!currentWorkspaceId ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-16"
          >
            <EmptyWorkspace
              icon={
                <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 shadow-glow">
                  <FolderPlus className="size-7 text-primary" />
                </div>
              }
              title="Create your first workspace"
              description="A workspace holds your research projects, papers, and AI team. You will only need to do this once."
              action={
                <Button
                  size="lg"
                  className="gap-2 rounded-xl px-6 shadow-glow"
                  disabled={createWorkspace.isPending}
                  onClick={handleStartFromEmpty}
                >
                  {createWorkspace.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  {createWorkspace.isPending ? "Creating…" : "Create workspace"}
                </Button>
              }
            />
          </motion.div>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="space-y-4 text-center"
            >
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.5, ease: "easeOut", delay: 0.05 }}
                className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent ring-1 ring-primary/10 shadow-glow"
              >
                <Sparkles className="size-7 text-primary" />
              </motion.div>
              <h1 className="text-balance text-[2rem] font-bold tracking-tight text-foreground sm:text-[2.5rem] md:text-[2.75rem] leading-[1.15]">
                What would you like to
                <br />
                <span className="bg-gradient-to-r from-primary via-[#a78bfa] to-primary bg-clip-text text-transparent">
                  research today?
                </span>
              </h1>
              <p className="mx-auto max-w-lg text-balance text-sm text-muted-foreground/80 leading-relaxed">
                Give AARA a topic. It searches the literature, finds gaps,
                generates ideas, and drafts papers — all in real time, right in
                front of you.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.12 }}
              className="mt-8 flex items-center justify-center gap-1.5 flex-wrap"
            >
              {PIPELINE_STEPS.map(({ icon: Icon, label, desc: _desc }, i) => (
                <React.Fragment key={label}>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.15 + i * 0.06 }}
                    className="group relative"
                  >
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/50 bg-card/50 px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 transition-all hover:border-primary/30 hover:bg-accent/50 hover:text-foreground hover:shadow-sm">
                      <Icon className="size-3" />
                      {label}
                    </span>
                  </motion.div>
                  {i < PIPELINE_STEPS.length - 1 && (
                    <ArrowRight className="size-2.5 shrink-0 text-muted-foreground/30" />
                  )}
                </React.Fragment>
              ))}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.18, ease: "easeOut" }}
              className="mt-8"
            >
              <form onSubmit={handleStart}>
                <div
                  className={cn(
                    "group relative rounded-2xl border bg-card/60 p-1.5 shadow-sm backdrop-blur-sm transition-all duration-300",
                    hasTopic
                      ? "border-primary/30 shadow-glow"
                      : "border-border/60 hover:border-border",
                    "focus-within:border-primary/40 focus-within:shadow-glow",
                  )}
                >
                  <div className="relative">
                    <textarea
                      ref={inputRef}
                      id="topic"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      rows={2}
                      placeholder={`e.g. ${TOPIC_EXAMPLES[exampleIndex]}`}
                      className="w-full resize-none rounded-xl border-0 bg-transparent px-4 py-3.5 text-base text-foreground placeholder:text-muted-foreground/50 focus-visible:outline-none md:text-lg leading-relaxed transition-all"
                      required
                    />
                    {showAdvanced && (
                      <div className="border-t border-border/40 px-4 py-3">
                        <div className="flex flex-col gap-3 sm:flex-row">
                          <div className="flex-1 space-y-1">
                            <label
                              htmlFor="direction"
                              className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70"
                            >
                              Research direction
                            </label>
                            <input
                              id="direction"
                              value={researchDirection}
                              onChange={(e) =>
                                setResearchDirection(e.target.value)
                              }
                              placeholder="Optional: narrow the focus"
                              className="w-full rounded-lg border border-input/60 bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            />
                          </div>
                          <div className="flex-1 space-y-1">
                            <label
                              htmlFor="maxPapers"
                              className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70"
                            >
                              Papers to review
                            </label>
                            <input
                              id="maxPapers"
                              type="number"
                              min={5}
                              max={200}
                              value={maxPapers}
                              onChange={(e) =>
                                setMaxPapers(Number(e.target.value) || 50)
                              }
                              className="w-full rounded-lg border border-input/60 bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 px-3 pb-2">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setShowAdvanced((s) => !s)}
                        className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-muted-foreground/70 transition-all hover:bg-accent/60 hover:text-foreground"
                      >
                        {showAdvanced ? "Hide options" : "Options"}
                      </button>
                      {hasTopic && (
                        <button
                          type="button"
                          onClick={handleGetSuggestions}
                          disabled={scoping.isPending}
                          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-muted-foreground/70 transition-all hover:bg-accent/60 hover:text-foreground disabled:opacity-50"
                        >
                          {scoping.isPending ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Sparkles className="size-3" />
                          )}
                          {scoping.isPending ? "Thinking…" : "AI scoping"}
                        </button>
                      )}
                    </div>

                    <Button
                      type="submit"
                      size="lg"
                      className={cn(
                        "gap-2 rounded-xl px-5 shadow-glow transition-all duration-300",
                        hasTopic &&
                          "bg-gradient-to-r from-primary to-[#7c3aed] hover:from-primary/90 hover:to-[#7c3aed]/90",
                      )}
                      disabled={!hasTopic || isStarting}
                    >
                      {isStarting ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <ArrowRight className="size-4" />
                      )}
                      {isStarting ? "Starting…" : "Start research"}
                    </Button>
                  </div>
                </div>
              </form>

              <LaunchSequence steps={launchSteps} visible={showLaunch} />

              <AnimatePresence>
                {scoping.data && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="mt-3"
                  >
                    <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-accent/60 to-card/60 p-4 text-sm text-foreground/90 shadow-sm">
                      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary/70">
                        <Sparkles className="size-3" />
                        AI Suggestion
                      </div>
                      {scoping.data.text}
                    </div>
                  </motion.div>
                )}
                {scoping.isError && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="mt-2 px-1 text-xs text-destructive/80"
                  >
                    Could not get suggestions. You can still start without them.
                  </motion.p>
                )}
              </AnimatePresence>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.3 }}
              className="mt-12"
            >
              <div className="mb-3 flex items-center justify-between">
                <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
                  <ListChecks className="size-3" />
                  Recent research
                </h2>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-muted-foreground/70 transition-all hover:bg-accent/50 hover:text-foreground"
                >
                  View all
                  <ChevronRight className="size-3" />
                </Link>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/40 p-2 shadow-sm">
                <RecentActivityList />
              </div>
            </motion.div>
          </>
        )}
      </div>
    </WorkspaceLayout>
  );
}
