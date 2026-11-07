/**
 * Demo personas. Each maps to a backend workspace role (owner/admin/analyst/viewer)
 * so the demo reflects the real RBAC model in apps/api.
 */
export type PersonaId = "owner" | "ops" | "analyst" | "accountant";

export type Persona = {
  id: PersonaId;
  name: string;
  initials: string;
  title: string;
  business: string;
  role: "owner" | "admin" | "analyst" | "viewer";
  quote: string;
  focus: string[];
  accent: string; // CSS colour token
  greeting: string;
};

export const PERSONAS: Persona[] = [
  {
    id: "owner",
    name: "Meera Kulkarni",
    initials: "MK",
    title: "Store owner",
    business: "Kulkarni General Stores · 3 outlets, Pune",
    role: "owner",
    quote: "I want to know where my profit went this month.",
    focus: ["Profit & margin", "Approve reorders", "Festive season prep"],
    accent: "var(--color-sindoor)",
    greeting: "Namaste Meera",
  },
  {
    id: "ops",
    name: "Arjun Mehta",
    initials: "AM",
    title: "Operations manager",
    business: "Mehta Lifestyle · apparel & home, Ahmedabad",
    role: "admin",
    quote: "Tell me what will run out before it does.",
    focus: ["Stock-out risk", "Reorder drafts", "Supplier lead times"],
    accent: "var(--color-haldi)",
    greeting: "Kem cho Arjun",
  },
  {
    id: "analyst",
    name: "Zoya Siddiqui",
    initials: "ZS",
    title: "Data analyst",
    business: "Noor Electronics · online + 2 stores, Lucknow",
    role: "analyst",
    quote: "Show me the drivers, not just the totals.",
    focus: ["Sales drivers", "Forecast accuracy", "Customer cohorts"],
    accent: "var(--color-mor)",
    greeting: "Adaab Zoya",
  },
  {
    id: "accountant",
    name: "Kabir Rao",
    initials: "KR",
    title: "Accountant · view only",
    business: "External CA for Kulkarni General Stores",
    role: "viewer",
    quote: "I need clean numbers that match the GST return.",
    focus: ["Net vs gross sales", "GST summary", "Exportable reports"],
    accent: "var(--color-neel)",
    greeting: "Namaskara Kabir",
  },
];

export const getPersona = (id: string | null | undefined) => PERSONAS.find((p) => p.id === id) ?? null;
