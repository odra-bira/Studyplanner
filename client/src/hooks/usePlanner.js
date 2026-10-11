// All planner state in one reducer, saved to localStorage.
import { useEffect, useReducer } from 'react';
import { addDays, parse, today } from '../lib/dates.js';

const STORAGE_KEY = 'studyease.v2';
export const newId = () => Math.random().toString(36).slice(2, 10);

/** The scenario from the project deck: a hard report due Friday, 3 hours at 1 hour a day. */
function exampleState() {
  const t = today();
  let fri = t;
  while (parse(fri).getDay() !== 5) fri = addDays(fri, 1);
  if (fri <= addDays(t, 1)) fri = addDays(fri, 7);
  const a = { id: newId(), title: 'Research report', course: 'WRT 105', due: fri, difficulty: 'hard', hours: 3 };
  const s = (offset, task, why) => ({ id: newId(), assignmentId: a.id, date: addDays(fri, offset), minutes: 60, task, why, done: false, steps: [] });
  return {
    daily: 60,
    mood: null,
    example: true,
    assignments: [a],
    sessions: [
      s(-2, 'Outline and sources', 'Hard work starts early, so the outline gets a full session before drafting.'),
      s(-1, 'Write a first draft', 'Drafting works from the outline while sources are still fresh.'),
      s(0, 'Review and submit', 'A short final pass on the due date, after a night away from the draft.'),
    ],
  };
}

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && Array.isArray(saved.assignments) && Array.isArray(saved.sessions)) return saved;
  } catch {
    /* fall through */
  }
  return exampleState();
}

function reducer(state, action) {
  switch (action.type) {
    case 'addPlan': {
      const base = state.example ? { ...state, assignments: [], sessions: [], example: false } : state;
      const sessions = action.sessions.map((s) => ({ id: newId(), assignmentId: action.assignment.id, done: false, steps: [], ...s }));
      return { ...base, assignments: [...base.assignments, action.assignment], sessions: [...base.sessions, ...sessions] };
    }
    case 'updateSession':
      return { ...state, sessions: state.sessions.map((s) => (s.id === action.id ? { ...s, ...action.patch } : s)) };
    case 'deleteSession':
      return { ...state, sessions: state.sessions.filter((s) => s.id !== action.id) };
    case 'deleteAssignment': {
      const assignments = state.assignments.filter((a) => a.id !== action.id);
      return { ...state, assignments, example: state.example && assignments.length > 0, sessions: state.sessions.filter((s) => s.assignmentId !== action.id) };
    }
    case 'applyMoves': {
      const byId = Object.fromEntries(action.moves.map((m) => [m.id, m]));
      return {
        ...state,
        sessions: state.sessions.map((s) => (byId[s.id] ? { ...s, date: byId[s.id].date, minutes: byId[s.id].minutes ?? s.minutes, why: byId[s.id].why || s.why } : s)),
      };
    }
    case 'setMood':
      return { ...state, mood: state.mood === action.mood ? null : action.mood };
    case 'setDaily':
      return { ...state, daily: action.daily };
    case 'clearExample':
      return { ...state, assignments: [], sessions: [], example: false };
    default:
      return state;
  }
}

export function usePlanner() {
  const [state, dispatch] = useReducer(reducer, undefined, load);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* storage full or blocked: the app still works for this visit */
    }
  }, [state]);
  return [state, dispatch];
}
