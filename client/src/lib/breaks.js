// Short, study-friendly jokes and riddles for the "How are you feeling?" break.
export const JOKES = [
  { q: 'Why did the student eat their homework?', a: 'The teacher said it was a piece of cake.' },
  { q: 'Why was the math book sad?', a: 'It had too many problems.' },
  { q: 'What do you call a sleeping bull?', a: 'A bulldozer.' },
  { q: 'Why did the computer go to the doctor?', a: 'It caught a virus.' },
  { q: 'Why don’t scientists trust atoms?', a: 'They make up everything.' },
  { q: 'What did the calculator say to the student?', a: 'You can count on me.' },
  { q: 'Why did the developer go broke?', a: 'They used up all their cache.' },
  { q: 'What’s a pencil’s favorite subject?', a: 'Draw-ing, obviously.' },
  { q: 'Why was the clock in the library?', a: 'It wanted to spend some time reading.' },
  { q: 'How does a student stay cool during exams?', a: 'They sit near the fans of the subject.' },
];

export const RIDDLES = [
  { q: 'What has keys but can’t open locks?', a: 'A keyboard (or a piano).', accept: ['keyboard', 'piano'] },
  { q: 'The more you take, the more you leave behind. What am I?', a: 'Footsteps.', accept: ['footstep', 'footprint', 'steps'] },
  { q: 'What gets wetter the more it dries?', a: 'A towel.', accept: ['towel'] },
  { q: 'I have cities but no houses, mountains but no trees, and water but no fish. What am I?', a: 'A map.', accept: ['map'] },
  { q: 'What can you catch but not throw?', a: 'A cold.', accept: ['cold'] },
  { q: 'What has a head and a tail but no body?', a: 'A coin.', accept: ['coin'] },
  { q: 'What goes up but never comes down?', a: 'Your age.', accept: ['age'] },
  { q: 'What has many words but never speaks?', a: 'A book.', accept: ['book'] },
  { q: 'I’m tall when I’m young and short when I’m old. What am I?', a: 'A candle.', accept: ['candle'] },
  { q: 'What can travel around the world while staying in a corner?', a: 'A stamp.', accept: ['stamp'] },
];

// Break length by stress check-in: low 1 min, medium 2 min, high 5 min.
export const BREAK_SECONDS = { low: 60, medium: 120, high: 300 };

// "What's behind it?" chips with a short, practical tip each.
export const REASONS = [
  { id: 'deadline', label: 'Deadlines', tip: 'Pick the one due soonest and do only the first 25 minutes of it.' },
  { id: 'workload', label: 'Too much work', tip: 'Write the tasks down, then circle just three for today.' },
  { id: 'sleep', label: 'Tired', tip: 'Drink some water and stretch. A short walk beats more coffee.' },
  { id: 'topic', label: 'Hard topic', tip: 'Switch to an easier task for now and come back to it fresh.' },
  { id: 'other', label: 'Something else', tip: 'Take a few slow breaths. It’s fine to start small.' },
];

// Gentle nudge shown with the break, keyed by the stress check-in.
export const MOOD_LINES = {
  low: 'Feeling good. A quick brain teaser keeps you sharp.',
  medium: 'Steady. Take a one-minute breather before the next session.',
  high: 'Stress is high. Step away for a minute and have a laugh.',
};
