/**
 * Duolingo-style microcopy library
 * Playful, encouraging, personality-driven UX writing
 */

const pick = <T>(arr: readonly T[]): T => arr[Math.floor(Math.random() * arr.length)];

// Success feedback - varied, celebratory, never boring
const SUCCESS_MESSAGES = [
  "Nailed it!",
  "You're on fire!",
  "Brilliant!",
  "Perfect!",
  "Exactly right!",
  "You got it!",
  "Impressive!",
  "Keep it up!",
  "Excellent work!",
  "That's the one!",
  "Spot on!",
  "You're crushing it!",
  "Nice one!",
  "Look at you go!",
  "Flawless!",
] as const;

const STREAK_SUCCESS = [
  "You're unstoppable!",
  "On a roll!",
  "Nothing can stop you!",
  "Streak master!",
  "You're in the zone!",
] as const;

// Error feedback - encouraging, never discouraging
const ERROR_MESSAGES = [
  "Almost there!",
  "Not quite, but close!",
  "Good try! Keep going.",
  "Oops! Let's try again.",
  "So close!",
  "One more try!",
  "You've got this!",
  "Learning in progress!",
] as const;

const ERROR_WITH_HINT = [
  "Here's a hint:",
  "Try thinking about:",
  "Remember:",
  "Quick tip:",
] as const;

// Typo-specific (close but not perfect)
const TYPO_MESSAGES = [
  "Almost perfect! Watch the spelling.",
  "So close! Just a small typo.",
  "Right idea! Check your letters.",
  "Nearly there! Double-check the spelling.",
] as const;

// Lesson intro hooks
const LESSON_HOOKS = [
  "Ready to level up?",
  "Let's learn something new!",
  "Time to expand your skills!",
  "Your brain is about to grow!",
  "Adventure awaits!",
  "Let's dive in!",
] as const;

// Module transitions
const MODULE_COMPLETE = [
  "Module complete!",
  "Another one down!",
  "Progress unlocked!",
  "Keep going!",
  "You're making progress!",
] as const;

// Lesson completion
const LESSON_COMPLETE = [
  "Lesson complete!",
  "You did it!",
  "Amazing work!",
  "Knowledge gained!",
  "Skills leveled up!",
] as const;

// Encouragement for continuing
const CONTINUE_PROMPTS = [
  "Ready for more?",
  "Keep the momentum!",
  "Let's keep going!",
  "You're just getting started!",
  "More to discover!",
] as const;

// Loading states - playful, not boring spinners
const LOADING_MESSAGES = [
  "Preparing your lesson...",
  "Loading new words...",
  "Getting things ready...",
  "Almost there...",
  "Warming up...",
] as const;

// Empty states
const NO_CONTENT = [
  "Coming soon!",
  "Still cooking!",
  "In the works!",
] as const;

// Streak messages
const STREAK_BUILDERS = {
  first: "First step! Keep it going tomorrow.",
  early: (days: number) => `${days} days strong! You're building a habit.`,
  solid: (days: number) => `${days} day streak! You're committed.`,
  impressive: (days: number) => `${days} days! You're unstoppable.`,
  legendary: (days: number) => `${days} days! Legendary dedication.`,
} as const;

// XP celebration messages
const XP_MESSAGES = [
  "XP earned!",
  "Points gained!",
  "Experience up!",
] as const;

// Heart loss messages (but encouraging)
const HEART_LOSS = [
  "Mistakes help you learn!",
  "Every error is a lesson!",
  "You'll get it next time!",
  "Part of the journey!",
] as const;

// Exercise-specific prompts (more engaging than generic)
const EXERCISE_PROMPTS = {
  word_bank: [
    "Tap the words in order",
    "Build the sentence",
    "Arrange the words",
  ],
  typing: [
    "Type your answer",
    "Write it out",
    "Show what you know",
  ],
  multiple_choice: [
    "Pick the right one",
    "Choose wisely",
    "Select your answer",
  ],
  matching: [
    "Match the pairs",
    "Find the connections",
    "Link them up",
  ],
  fill_blank: [
    "Complete the sentence",
    "Fill in the gap",
    "What goes here?",
  ],
  pattern_fill: [
    "Apply the pattern",
    "Use what you learned",
    "Complete the form",
  ],
} as const;

// Export functions for easy use
export const microcopy = {
  success: (streak = 0) => streak >= 3 ? pick(STREAK_SUCCESS) : pick(SUCCESS_MESSAGES),
  error: () => pick(ERROR_MESSAGES),
  errorHint: () => pick(ERROR_WITH_HINT),
  typo: () => pick(TYPO_MESSAGES),
  lessonHook: () => pick(LESSON_HOOKS),
  moduleComplete: () => pick(MODULE_COMPLETE),
  lessonComplete: () => pick(LESSON_COMPLETE),
  continuePrompt: () => pick(CONTINUE_PROMPTS),
  loading: () => pick(LOADING_MESSAGES),
  noContent: () => pick(NO_CONTENT),
  xp: () => pick(XP_MESSAGES),
  heartLoss: () => pick(HEART_LOSS),
  
  streak: (days: number) => {
    if (days <= 1) return STREAK_BUILDERS.first;
    if (days <= 7) return STREAK_BUILDERS.early(days);
    if (days <= 30) return STREAK_BUILDERS.solid(days);
    if (days <= 100) return STREAK_BUILDERS.impressive(days);
    return STREAK_BUILDERS.legendary(days);
  },
  
  exercisePrompt: (type: keyof typeof EXERCISE_PROMPTS) => 
    pick(EXERCISE_PROMPTS[type] ?? EXERCISE_PROMPTS.multiple_choice),
};

export default microcopy;
