# Learn Path UX Design Document

> Design rationale for Lingua's Duolingo-inspired learning path interface

---

## 1. User Mental Model Mapping

### What Users Think They're Doing
| User Belief | System Reality | Design Implication |
|-------------|----------------|-------------------|
| "I'm progressing through lessons" | SRS schedules reviews based on memory decay | Show progress as a journey, not a queue |
| "Completing units unlocks new content" | Pattern mastery unlocks complexity tiers | Gate nodes visually, unlock automatically |
| "Stars/XP = I'm learning" | Quality reviews strengthen memory traces | Reward review quality, not just completion |
| "I need to practice weak areas" | SM-2 surfaces struggling patterns | Highlight "needs practice" without shame |

### User Vocabulary Alignment
- **Unit** → Group of related syntactic patterns (e.g., "Genitive Case")
- **Lesson** → A set of sentences targeting specific patterns
- **Level** → Mastery tier (0-5, displayed as progress rings)
- **Crown** → Completing all levels in a unit
- **Streak** → Consecutive days with completed reviews

### Expected Outcomes by Interaction
| Interaction | User Expects | We Deliver |
|-------------|--------------|------------|
| Tap node | Start lesson immediately | If unlocked, start; if locked, show prereqs |
| Complete session | See progress update | Animate progress ring, celebrate milestones |
| Return to app | See where to continue | Highlight "continue" node with pulsing CTA |
| Scroll path | Explore future content | Preview locked units with blur/opacity |

---

## 2. Interaction Pattern Audit (Existing Lingua Patterns)

### Patterns to Preserve (Consistency)
1. **Card-based containers** - White bg, rounded-3xl, shadow-xl, border
2. **Animation library** - framer-motion for all transitions
3. **Progress feedback** - motion.div width animations for progress bars
4. **Color system** - primary-500/600 (sky blue), success green-500, warning amber
5. **Empty states** - Centered icon + message + CTA pattern
6. **Loading states** - Spinning border-b-2 with primary color
7. **Button hierarchy** - Primary (filled), secondary (outlined), ghost (text)

### New Patterns Needed
1. **Node states** - current, completed, locked, needs-practice
2. **Path visualization** - Vertical scrolling tree with branching
3. **Unit headers** - Sticky section dividers
4. **Skill rings** - Circular progress indicators (0-5 levels)
5. **Milestone celebrations** - Full-screen confetti/animation on unit completion

---

## 3. Critical Path Analysis

### Primary Flow: Daily Review Session
```
[Open App] → [See Path] → [Identify Continue Point] → [Tap Node] → [Complete Review] → [See Progress] → [Close/Continue]
     │              │                │                      │                │
     ↓              ↓                ↓                      ↓                ↓
  < 100ms      Highlighted       Pulsing CTA          Instant load      Animate ring
```

**Minimum Interactions**: 2 taps (node → complete)
**Target Time to First Interaction**: < 3 seconds

### Secondary Flow: Exploring Locked Content
```
[See Locked Node] → [Tap] → [See Requirements] → [Navigate to Prereq] → [Complete] → [Return, Unlocked]
```

**Design Decision**: Tapping locked nodes shows a modal with:
- What patterns are needed
- Direct link to the blocking unit
- Estimated time to unlock

---

## 4. Hesitation Points & Error Prevention

### Where Users Will Hesitate

| Point | Reason | Solution |
|-------|--------|----------|
| First node tap | Uncertainty about time commitment | Show "~5 min" duration on node |
| After completion | What now? | Auto-scroll to next node, pulse it |
| Seeing many locked nodes | Overwhelm | Blur locked nodes, focus on current |
| Returning after break | Lost context | "Continue where you left off" banner |

### Error States & Recovery

| Error | User Action | Response |
|-------|-------------|----------|
| Network failure mid-session | Tap submit | Queue locally, sync on reconnect, show indicator |
| Tap locked node | Tap | Gentle shake + tooltip, not error modal |
| App kill during review | Close app | Resume exactly where left off on return |
| Skip too many reviews | Avoid app | No punishment; welcome back warmly |

---

## 5. State Design Matrix

Each view component handles these states:

### Path View States
| State | Visual Treatment | Transition |
|-------|------------------|------------|
| **Empty** (new user) | Welcome card + first unit | Fade in with stagger |
| **Loading** | Skeleton path with pulsing nodes | Shimmer effect |
| **Partial** (some units) | Path with mix of states | Standard |
| **Error** (fetch failed) | Retry card, offline indicator | Fade in |
| **Success** (full data) | Complete path visualization | Fade in with stagger |

### Node States
| State | Visual | Ring | Glow | Interactive |
|-------|--------|------|------|-------------|
| **Locked** | Grayscale, 50% opacity | Empty, dashed | None | Shake on tap |
| **Available** | Full color | Empty, solid | Subtle pulse | Yes |
| **Current** | Full color + "START" badge | Partial fill | Strong pulse | Yes |
| **In Progress** | Full color | Partial fill | None | Yes |
| **Completed** | Full color + check | Full fill | None | Yes (practice) |
| **Needs Practice** | Full color + warning dot | Partial (decayed) | Orange pulse | Yes |
| **Crowned** | Gold + crown icon | Gold fill | Sparkle | Practice mode only |

---

## 6. Information Architecture

### Path Structure
```
Section 1: Foundations
├── Unit 1: Basic Noun Cases (NOM, ACC)
│   ├── Node: Nominative Singular
│   ├── Node: Accusative Singular
│   └── Node: Mixed Practice
├── Unit 2: Genitive Introduction
│   ├── Node: Genitive Singular
│   └── Node: Possession Expressions
└── [Checkpoint: Section 1 Review]

Section 2: Verbal System
├── Unit 3: Present Tense
│   ...
```

### Visual Hierarchy
1. **Section** - Full-width banner, sticky on scroll
2. **Unit** - Collapsible card with title + description
3. **Node** - Interactive circle with skill ring
4. **Checkpoint** - Special unit-wide review node

---

## 7. Reversibility Over Confirmation

### Principles Applied
| Action | Old Pattern | New Pattern |
|--------|-------------|-------------|
| Exit mid-lesson | "Are you sure?" modal | Silent save, resume on return |
| Skip question | Confirmation dialog | Undo button for 5 seconds |
| Reset progress | Confirmation + type text | Hidden in settings, 24hr undo period |
| Rate answer wrong | Final immediately | Brief undo window |

### Undo Implementation
```typescript
// After any destructive action
showUndoToast({
  message: "Progress saved",
  action: "Undo",
  duration: 5000,
  onUndo: () => revertLastAction()
});
```

---

## 8. System Status Feedback

### Passive Indicators (No Attention Demanded)
- Streak flame icon in header (number visible on hover)
- Subtle progress bar at bottom of viewport
- Node rings update in real-time as siblings complete
- "Last practiced" timestamp on nodes (on hover)

### Active Notifications (User Glance Required)
- Review reminder badge on "Learn" nav item
- "New unit unlocked!" animation (once, dismissible)
- Daily goal progress ring in corner

### Never Interrupt
- No modals for "great job" (use inline celebration)
- No push for premium (non-existent feature)
- No social prompts (learning is personal)

---

## 9. Responsive Behavior

### Mobile (< 768px)
- Single-column path, nodes centered
- Swipe to reveal node options (practice, info)
- Bottom sheet for node details
- Larger touch targets (min 48px)

### Tablet (768px - 1024px)
- Path with slight zigzag for visual interest
- Side panel for unit details
- Gestures: pinch to zoom path overview

### Desktop (> 1024px)
- Path on left, detail panel on right
- Keyboard navigation (j/k for nodes, Enter to start)
- Hover states with rich tooltips

---

## 10. Animation Specifications

### Path Load
```css
/* Nodes stagger in from top */
animation: fadeSlideUp 0.4s ease-out;
animation-delay: calc(var(--node-index) * 50ms);
```

### Node Completion
```css
/* Ring fills with easing */
transition: stroke-dashoffset 0.8s cubic-bezier(0.65, 0, 0.35, 1);

/* Celebration burst */
@keyframes burst {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.5; }
  100% { transform: scale(2); opacity: 0; }
}
```

### Unlock Transition
```css
/* Locked → Available */
transition: filter 0.5s ease-out, opacity 0.5s ease-out;
filter: grayscale(0);
opacity: 1;
```

---

## 11. Accessibility Considerations

- **Screen readers**: Nodes announce state ("Lesson 1, Nominative Case, completed, level 3 of 5")
- **Keyboard**: Full tab navigation, Enter to start, Escape to close modals
- **Reduced motion**: Disable animations, use opacity transitions only
- **Color blindness**: Never rely solely on color; use icons + patterns
- **Focus indicators**: Visible focus rings on all interactive elements

---

## 12. Implementation Priority

### Phase 1: Core Path (MVP)
1. Path visualization with unit/node structure
2. Node states (locked, available, current, completed)
3. Tap to start review session
4. Progress ring animation

### Phase 2: Polish
1. Section headers with sticky behavior
2. Milestone celebrations
3. Needs-practice state with decay visualization
4. Undo system

### Phase 3: Delight
1. Streaks and daily goals
2. Path overview zoom
3. Keyboard navigation
4. Confetti on unit completion

---

## 13. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to first lesson | < 10 seconds | Analytics: app_open → lesson_start |
| Session completion rate | > 80% | Analytics: lesson_start → lesson_complete |
| Return rate (D1) | > 60% | Analytics: unique users day over day |
| Path scroll depth | > 3 units | Analytics: scroll events on path |

---

## Appendix: Component Breakdown

```
LearnPath/
├── index.tsx           # Main container, data fetching
├── PathView.tsx        # Scrollable path visualization
├── SectionHeader.tsx   # Sticky section dividers
├── UnitCard.tsx        # Collapsible unit container
├── SkillNode.tsx       # Individual lesson node
├── SkillRing.tsx       # SVG progress ring
├── CurrentIndicator.tsx # Pulsing "START" badge
├── LockedOverlay.tsx   # Blur + lock icon for gated content
├── MilestoneModal.tsx  # Celebration on unit completion
└── DESIGN.md           # This document
```

