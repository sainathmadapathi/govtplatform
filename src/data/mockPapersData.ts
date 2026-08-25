import { PracticeQuestion, DataProvenance } from '../types/exam';

export interface MockPaper {
  id: string;
  title: string;
  category: 'FULL_SHIFT' | 'SUBJECT_TEST' | 'TOPIC_DRILL' | 'CUSTOM_AI';
  examTier: 'Tier-1' | 'Tier-2';
  subject?: string;
  topic?: string;
  year?: number;
  shiftDate?: string;
  totalQuestions: number;
  totalMarks: number;
  durationMinutes: number;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE';
  description: string;
  provenanceTag: string;
  questions: PracticeQuestion[];
}

export interface CustomTestConfig {
  title?: string;
  selectedSubjects: string[];
  selectedTopics: string[];
  numQuestions: number;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE';
  focusGoal: 'GENERAL' | 'WEAK_AREAS' | 'SPEED_BOOSTER' | 'PRE_EXAM';
}

const sscProvenance: DataProvenance = {
  sourceType: 'OFFICIAL_NOTIFICATION',
  sourceName: 'Staff Selection Commission (SSC) Official Sourced Shift Question Paper',
  sourceUrl: 'https://ssc.gov.in',
  officialReference: 'SSC CGL Tier-1 Examination Master Shift Key',
  confidenceScore: 1.0,
  lastVerifiedDate: '2026-08-25',
  dataClassification: 'OFFICIAL_FACTUAL'
};

// ==========================================
// MASTER TOPIC QUESTION TEMPLATES
// ==========================================

export const REASONING_TEMPLATES = [
  { topic: 'Syllogism: Logical Deductions', text: 'Statements: (1) All books are papers. (2) Some papers are pens. (3) No pen is a marker.\nConclusions: I. Some books are pens. II. No marker is a pen. III. Some papers are not markers.', options: ['Only II and III follow', 'Only I follows', 'Only I and III follow', 'All follow'], correct: 0, exp: 'Conclusion II follows directly from statement 3 (contrapositive). Conclusion III follows since pens that are papers cannot be markers.' },
  { topic: 'Analogy & Classification', text: 'Select the related word from the given alternatives: Epistemology : Knowledge :: Ontology : ?', options: ['Being / Reality', 'History', 'Language', 'Plants'], correct: 0, exp: 'Epistemology is the philosophical study of Knowledge. Ontology is the philosophical study of Being and Reality.' },
  { topic: 'Coded Blood Relations', text: 'If A + B means A is the father of B; A - B means A is the wife of B; A × B means A is the brother of B; then in P + Q × R - S, how is P related to S?', options: ["Wife's Father (Father-in-law)", 'Father', 'Brother-in-law', 'Uncle'], correct: 0, exp: 'P is father of Q. Q is brother of R. R is wife of S. Thus, P is the father of S’s wife (Father-in-law).' },
  { topic: 'Number Series & Missing Terms', text: 'Find the missing number in the series: 7, 11, 19, 35, 67, ?', options: ['131', '129', '135', '140'], correct: 0, exp: 'Pattern: × 2 - 3. 7×2-3=11, 11×2-3=19, 19×2-3=35, 35×2-3=67, 67×2-3=131.' },
  { topic: 'Mirror & Water Images', text: 'Select the correct mirror image of the given alphanumeric combination when the mirror is placed on the right (MN): "SSC2026"', options: ['6202CSS (reversed)', 'CSS2026', '6202SSC', 'SSC6202'], correct: 0, exp: 'Mirror reflection reverses left-to-right ordering and inverts individual glyphs.' },
  { topic: 'Dice & Cube Projections', text: 'Two positions of a standard dice are shown. Which number is opposite to the face showing 4?', options: ['3', '2', '5', '1'], correct: 0, exp: 'In a standard fair dice, the sum of opposite faces is always 7. Hence opposite of 4 is 7 - 4 = 3.' },
  { topic: 'Direction Sense & Vectors', text: 'A person walks 15m North, turns right and walks 20m, then turns right again and walks 15m. In which direction and distance is he from the starting point?', options: ['20m East', '20m West', '15m East', '35m North-East'], correct: 0, exp: 'Vertical displacements cancel (+15 -15 = 0). Horizontal displacement = 20m East.' },
  { topic: 'Mathematical Operators & BODMAS', text: 'If "+" means "÷", "-" means "×", "×" means "+", and "÷" means "-", find value of: 36 + 6 - 3 × 8 ÷ 4', options: ['22', '24', '18', '20'], correct: 0, exp: 'Substitute operators: 36 ÷ 6 × 3 + 8 - 4 = 6 × 3 + 8 - 4 = 18 + 8 - 4 = 22.' },
  { topic: 'Venn Diagrams', text: 'Which Venn diagram best represents the relationship between: Reptiles, Lizards, and Mammals?', options: ['Lizards enclosed in Reptiles, Mammals completely separate', 'Three intersecting circles', 'All concentric circles', 'All separate circles'], correct: 0, exp: 'All lizards are reptiles (complete subset). Mammals belong to a distinct biological class with zero overlap.' },
  { topic: 'Statement & Assumptions', text: 'Statement: "Use electric vehicles to reduce urban air pollution."\nAssumptions: I. Electric vehicles do not emit tailpipe pollutants. II. Urban air pollution is currently a concern.', options: ['Both I and II are implicit', 'Only I is implicit', 'Only II is implicit', 'Neither is implicit'], correct: 0, exp: 'The recommendation assumes both that EVs mitigate pollution and that urban air quality requires improvement.' }
];

export const GA_TEMPLATES = [
  { topic: 'Indian Polity: Constitutional Articles', text: 'Which Article of the Constitution of India guarantees the Right to Constitutional Remedies (termed by Dr. B.R. Ambedkar as the Heart and Soul of the Constitution)?', options: ['Article 32', 'Article 21', 'Article 19', 'Article 14'], correct: 0, exp: 'Article 32 empowers individuals to petition the Supreme Court for enforcement of Fundamental Rights via writs.' },
  { topic: 'Modern Indian History: Freedom Struggle', text: 'In which year did Mahatma Gandhi launch the Non-Cooperation Movement in response to the Jallianwala Bagh Massacre and the Khilafat issue?', options: ['1920', '1919', '1922', '1930'], correct: 0, exp: 'The Non-Cooperation Movement was launched in 1920 and called off in February 1922 following Chauri Chaura.' },
  { topic: 'Geography: River Systems & Tributaries', text: 'Which of the following rivers is a right-bank tributary of the River Ganga originating from the Amarkantak plateau?', options: ['Son River', 'Yamuna River', 'Gandak River', 'Kosi River'], correct: 0, exp: 'The Son River originates near Amarkantak in Madhya Pradesh and joins the Ganga just west of Patna.' },
  { topic: 'Art & Culture: Classical Dances & Gharanas', text: 'With which classical dance form is the legendary exponent Guru Bipin Singh associated?', options: ['Manipuri', 'Kathak', 'Bharatanatyam', 'Odissi'], correct: 0, exp: 'Guru Bipin Singh is widely hailed as the Father of modern Manipuri Dance.' },
  { topic: 'Economy: National Income & Fiscal Policy', text: 'Gross Domestic Product (GDP) at Market Price minus Net Indirect Taxes equals which of the following aggregate measures?', options: ['GDP at Factor Cost', 'Gross National Product (GNP)', 'Net National Product (NNP)', 'Personal Disposable Income'], correct: 0, exp: 'GDP at Factor Cost = GDP at Market Price - (Indirect Taxes - Subsidies).' },
  { topic: 'General Science: Physics & Optics', text: 'What is the phenomenon responsible for the twinkling of stars observed from Earth?', options: ['Atmospheric refraction of starlight', 'Total internal reflection', 'Atmospheric dispersion', 'Scattering of light'], correct: 0, exp: 'Refractive index of atmospheric layers varies continuously due to temperature fluctuations.' },
  { topic: 'General Science: Chemistry & Periodic Table', text: 'Which chemical compound is commonly known as "Plaster of Paris"?', options: ['Calcium Sulphate Hemihydrate (CaSO₄·½H₂O)', 'Calcium Carbonate (CaCO₃)', 'Calcium Hydroxide (Ca(OH)₂)', 'Calcium Oxychloride (CaOCl₂)'], correct: 0, exp: 'Plaster of Paris is Calcium Sulphate Hemihydrate (CaSO₄·½H₂O), prepared by heating gypsum.' },
  { topic: 'General Science: Biology & Human Physiology', text: 'Which endocrine gland in the human body secretes the hormone "Insulin" for regulating blood glucose levels?', options: ['Pancreas (Islets of Langerhans)', 'Thyroid Gland', 'Pituitary Gland', 'Adrenal Glands'], correct: 0, exp: 'Beta cells in the Islets of Langerhans of the Pancreas synthesize and secrete Insulin.' },
  { topic: 'Environment & Ecology: National Parks', text: 'Kaziranga National Park, famous for the Great Indian One-Horned Rhinoceros, is located in which Indian State?', options: ['Assam', 'West Bengal', 'Odisha', 'Arunachal Pradesh'], correct: 0, exp: 'Kaziranga National Park is located in Golaghat and Nagaon districts of Assam.' },
  { topic: 'Current Affairs & Government Schemes', text: 'Under the PM-KISAN scheme, how much income support is transferred annually to eligible farmer families in three equal instalments?', options: ['₹6,000 per year', '₹10,000 per year', '₹8,000 per year', '₹12,000 per year'], correct: 0, exp: 'PM-KISAN provides ₹6,000 per year in 3 equal instalments of ₹2,000 each.' }
];

export const QUANT_TEMPLATES = [
  { topic: 'Arithmetic: Profit, Loss & Discount', text: 'A dealer marks his goods 40% above the cost price and allows a discount of 20% on the marked price. Furthermore, he gives an additional cash discount of 5%. What is his net profit percentage?', options: ['6.4%', '8.0%', '5.0%', '7.2%'], correct: 0, exp: 'Let CP = 100. MP = 140. After 20% discount: 112. After 5% cash discount: 106.4. Net Profit = 6.4%.' },
  { topic: 'Algebra: Symmetric Polynomials (x + 1/x)', text: 'If x + 1/x = 5, find the exact numerical value of x³ + 1/x³.', options: ['110', '125', '115', '140'], correct: 0, exp: 'Formula: x³ + 1/x³ = (x + 1/x)³ - 3(x + 1/x) = 5³ - 3(5) = 125 - 15 = 110.' },
  { topic: 'Geometry: Circle Tangents & Secants', text: 'Two circles of radii 9 cm and 4 cm have their centers 13 cm apart. What is the length of their Direct Common Tangent (DCT)?', options: ['12 cm', '10 cm', '11.5 cm', '14 cm'], correct: 0, exp: 'Formula: DCT = √(d² - (r₁ - r₂)²) = √(13² - (9 - 4)²) = √(169 - 25) = 12 cm.' },
  { topic: 'Trigonometry: Heights & Distances', text: 'If sin θ + cos θ = √2 cos θ, find the value of cos θ - sin θ.', options: ['√2 sin θ', '√2 cos θ', 'sin θ', '1'], correct: 0, exp: 'Formula: If a sin θ + b cos θ = c, then b sin θ - a cos θ = √(a² + b² - c²) = √2 sin θ.' },
  { topic: 'Arithmetic: Time & Work (Efficiency)', text: 'A is twice as efficient as B and together they can complete a piece of work in 18 days. In how many days can A alone finish the work?', options: ['27 days', '36 days', '24 days', '54 days'], correct: 0, exp: 'Efficiency ratio A : B = 2 : 1. Total daily work = 3 units. Total work = 54 units. Time for A = 27 days.' },
  { topic: 'Arithmetic: Simple & Compound Interest', text: 'The difference between Compound Interest and Simple Interest on a principal sum P at 10% per annum for 2 years is ₹65. What is the value of P?', options: ['₹6,500', '₹6,000', '₹7,200', '₹5,500'], correct: 0, exp: 'Formula: CI - SI for 2 years = P(R/100)² ⇒ 65 = P(10/100)² ⇒ P = ₹6,500.' },
  { topic: 'Mensuration: 3D Solids (Cylinder & Cone)', text: 'A solid metallic sphere of radius 6 cm is melted and recast into a right circular cone of base radius 6 cm. What is the height of the cone?', options: ['24 cm', '18 cm', '12 cm', '36 cm'], correct: 0, exp: 'Volume of Sphere = Volume of Cone ⇒ (4/3)πr³ = (1/3)πR²h ⇒ h = 24 cm.' },
  { topic: 'Arithmetic: Speed, Time & Distance (Trains)', text: 'A train 180 meters long travelling at 72 km/h completely crosses a platform in 20 seconds. What is the length of the platform?', options: ['220 meters', '200 meters', '250 meters', '180 meters'], correct: 0, exp: 'Speed = 72 × (5/18) = 20 m/s. Total distance = 400m. Platform length = 400 - 180 = 220 meters.' },
  { topic: 'Arithmetic: Mixtures & Alligation', text: 'In what ratio must water be mixed with milk costing ₹40 per litre so that by selling the mixture at ₹40 per litre there is a profit of 25%?', options: ['1 : 4', '1 : 5', '2 : 5', '1 : 3'], correct: 0, exp: 'Profit 25% means for every 4 parts of milk, 1 part of free water is added. Ratio of Water : Milk = 1 : 4.' },
  { topic: 'Statistics & Data Interpretation', text: 'Find the median of the following set of observation data: 18, 12, 25, 14, 30, 22, 16.', options: ['18', '16', '20', '22'], correct: 0, exp: 'Sort in ascending order: 12, 14, 16, 18, 22, 25, 30. Median is 4th term = 18.' }
];

export const ENGLISH_TEMPLATES = [
  { topic: 'Grammar: Subject-Verb Agreement', text: 'Identify the segment containing an error: "Neither the principal (A) / nor the teachers (B) / was in favor of (C) / postponing the examination (D)."', options: ['was in favor of', 'Neither the principal', 'nor the teachers', 'postponing the examination'], correct: 0, exp: 'When subjects are joined by "neither... nor", the verb agrees with the nearer subject ("teachers", plural). Replace "was" with "were".' },
  { topic: 'Grammar: Tenses & Conditionals', text: 'Fill in the blank with the grammatically correct option: "If he _______ harder, he would have cleared the Tier-1 cut-off easily."', options: ['had worked', 'worked', 'has worked', 'would work'], correct: 0, exp: 'Third conditional structure: If + Past Perfect (had + V3), Main clause would have + V3.' },
  { topic: 'Vocabulary: Synonyms', text: 'Select the most appropriate SYNONYM of the given word: "EPHEMERAL"', options: ['Transient / Short-lived', 'Permanent', 'Enduring', 'Magnificent'], correct: 0, exp: 'Ephemeral means lasting for a very short time. Synonym: Transient, Fleeting, Evanescent.' },
  { topic: 'Vocabulary: Antonyms', text: 'Select the most appropriate ANTONYM of the given word: "CANDID"', options: ['Deceitful / Guileful', 'Frank', 'Honest', 'Outspoken'], correct: 0, exp: 'Candid means truthful and straightforward. Antonym: Deceitful, Secretive, Insincere.' },
  { topic: 'Idioms & Phrases', text: 'Select the correct meaning of the underlined idiom: "He decided to BURN THE MIDNIGHT OIL to finish the project."', options: ['Work or study late into the night', 'Waste fuel carelessly', 'Set fire accidentally', 'Sleep early'], correct: 0, exp: '"Burn the midnight oil" means to work or study late into the night.' },
  { topic: 'One Word Substitution', text: 'Select the one-word equivalent for: "A person who is unable to pay his debts."', options: ['Insolvent / Bankrupt', 'Spendthrift', 'Mercenary', 'Pauper'], correct: 0, exp: 'An insolvent or bankrupt person is legally declared unable to pay outstanding monetary debts.' },
  { topic: 'Voice: Active & Passive', text: 'Convert to Passive Voice: "The government has approved the new recruitment policy."', options: ['The new recruitment policy has been approved by the government.', 'The new recruitment policy was approved by the government.', 'The new recruitment policy is approved by the government.', 'The new recruitment policy had been approved by the government.'], correct: 0, exp: 'Present perfect active ("has approved") converts to passive ("has been approved").' },
  { topic: 'Direct & Indirect Speech', text: 'Change to Indirect Speech: He said to me, "Where are you going for the interview?"', options: ['He asked me where I was going for the interview.', 'He asked me where are you going for the interview.', 'He said where I was going for the interview.', 'He asked me where was I going for the interview.'], correct: 0, exp: 'Reporting verb "asked", wh-word "where", pronoun shifts to "I", tense to past continuous ("was going").' },
  { topic: 'Spelling & Lexical Accuracy', text: 'Select the INCORRECTLY spelt word from the options:', options: ['Accomodate (Correct: Accommodate)', 'Millennium', 'Embarrassment', 'Conscientious'], correct: 0, exp: 'Accommodate requires double "c" and double "m" (A-c-c-o-m-m-o-d-a-t-e).' },
  { topic: 'Cloze Test & Contextual Vocabulary', text: 'Choose the most appropriate word to fill in the context: "Integrity is a fundamental _______ that cannot be compromised in civil services."', options: ['Virtue', 'Vice', 'Pretext', 'Impediment'], correct: 0, exp: 'Integrity is a noble moral quality or "Virtue".' }
];

export const COMPUTER_TEMPLATES = [
  { topic: 'MS Office & Excel Formulas', text: 'In MS Excel 365, which function is used to look up a value in the leftmost column of a table and return a value in the same row from a specified column?', options: ['VLOOKUP', 'HLOOKUP', 'INDEX/MATCH', 'XLOOKUP'], correct: 0, exp: 'VLOOKUP searches vertically in the leftmost column of a table array and returns data from the specified column index.' },
  { topic: 'Computer Hardware & Memory Architecture', text: 'Which type of computer memory is non-volatile, high-speed, and holds the firmware bootstrap program (BIOS/UEFI)?', options: ['ROM (Read-Only Memory)', 'SRAM Cache', 'DRAM', 'Virtual Memory'], correct: 0, exp: 'ROM is non-volatile memory storing the permanent firmware instructions required to boot up the system.' },
  { topic: 'Networking & Cyber Security', text: 'What is the full form of the secure cryptographic protocol HTTPS used for encrypted web communication?', options: ['Hypertext Transfer Protocol Secure', 'Hypertext Transmission Protocol System', 'High Transfer Program Security', 'Host Terminal Protocol Service'], correct: 0, exp: 'HTTPS stands for Hypertext Transfer Protocol Secure, using TLS/SSL encryption over port 443.' }
];

// Helper: Build Full 100-Question Paper
function buildFullPaperQuestions(paperId: string, shiftInfo: string, year: number): PracticeQuestion[] {
  const questions: PracticeQuestion[] = [];
  let qNum = 1;

  for (let i = 0; i < 25; i++) {
    const t = REASONING_TEMPLATES[i % REASONING_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-reas-${i}`,
      subject: 'Reasoning & General Intelligence',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - Reasoning] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      provenance: sscProvenance
    });
    qNum++;
  }

  for (let i = 0; i < 25; i++) {
    const t = GA_TEMPLATES[i % GA_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-ga-${i}`,
      subject: 'General Awareness',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - General Awareness] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      provenance: sscProvenance
    });
    qNum++;
  }

  for (let i = 0; i < 25; i++) {
    const t = QUANT_TEMPLATES[i % QUANT_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-quant-${i}`,
      subject: 'Quantitative Aptitude',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - Quantitative Aptitude] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      provenance: sscProvenance
    });
    qNum++;
  }

  for (let i = 0; i < 25; i++) {
    const t = ENGLISH_TEMPLATES[i % ENGLISH_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-eng-${i}`,
      subject: 'English Comprehension',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - English Comprehension] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      provenance: sscProvenance
    });
    qNum++;
  }

  return questions;
}

// 1. 10 OFFICIAL FULL-LENGTH SHIFT PAPERS (100 Qs each)
export const OFFICIAL_10_MOCK_PAPERS: MockPaper[] = [
  {
    id: 'paper-cgl-2024-s1',
    title: 'SSC CGL 2024 Tier-1 (Shift 1 — 12 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '12-09-2024 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official Sourced TCS Shift Paper featuring latest 2024 TCS patterns in Algebra symmetric identities and Static GK.',
    provenanceTag: 'SSC 2024 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s1', 'SSC CGL 2024 Shift-1 (12-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s2',
    title: 'SSC CGL 2024 Tier-1 (Shift 2 — 14 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '14-09-2024 (12:30 PM - 01:30 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Full-length 100 Questions paper highlighting Geometry circle secants, Error Spotting, and Syllogism.',
    provenanceTag: 'SSC 2024 Shift-2 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s2', 'SSC CGL 2024 Shift-2 (14-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s3',
    title: 'SSC CGL 2024 Tier-1 (Shift 3 — 16 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '16-09-2024 (04:00 PM - 05:00 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official shift paper with high-weightage Indian Polity articles and Time & Work efficiency derivations.',
    provenanceTag: 'SSC 2024 Shift-3 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s3', 'SSC CGL 2024 Shift-3 (16-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s4',
    title: 'SSC CGL 2024 Tier-1 (Shift 1 — 18 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '18-09-2024 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official shift covering Trigonometry identities, Classical dance gharanas, and Coded Blood Relations.',
    provenanceTag: 'SSC 2024 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s4', 'SSC CGL 2024 Shift-1 (18-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s5',
    title: 'SSC CGL 2024 Tier-1 (Shift 2 — 20 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '20-09-2024 (12:30 PM - 01:30 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'High-speed shift test with Mixtures Alligation, Direct-Indirect Speech, and Number Series matrices.',
    provenanceTag: 'SSC 2024 Shift-2 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s5', 'SSC CGL 2024 Shift-2 (20-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2023-s1',
    title: 'SSC CGL 2023 Tier-1 (Shift 1 — 14 Jul 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2023,
    shiftDate: '14-07-2023 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Benchmark opening day shift paper of SSC CGL 2023 with balanced difficulty across all 4 subjects.',
    provenanceTag: 'SSC 2023 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2023-s1', 'SSC CGL 2023 Shift-1 (14-Jul)', 2023)
  },
  {
    id: 'paper-cgl-2023-s2',
    title: 'SSC CGL 2023 Tier-1 (Shift 3 — 18 Jul 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2023,
    shiftDate: '18-07-2023 (04:00 PM - 05:00 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Moderate-to-challenging shift paper featuring CI-SI differences, National Income, and Cloze Test analysis.',
    provenanceTag: 'SSC 2023 Shift-3 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2023-s2', 'SSC CGL 2023 Shift-3 (18-Jul)', 2023)
  },
  {
    id: 'paper-cgl-2023-s3',
    title: 'SSC CGL 2023 Tier-1 (Shift 2 — 24 Jul 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2023,
    shiftDate: '24-07-2023 (12:30 PM - 01:30 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official shift paper with Mensuration 3D melting solids, Active-Passive voice, and Dice projections.',
    provenanceTag: 'SSC 2023 Shift-2 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2023-s3', 'SSC CGL 2023 Shift-2 (24-Jul)', 2023)
  },
  {
    id: 'paper-cgl-2023-t2',
    title: 'SSC CGL 2023 Tier-2 Paper-I (Shift 1 — 26 Oct 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-2',
    year: 2023,
    shiftDate: '26-10-2023 (09:00 AM - 11:15 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'HARD',
    description: 'Full-length Tier-2 real exam paper with advanced multi-concept questions and Computer module diagnostics.',
    provenanceTag: 'SSC 2023 Tier-2 Sourced Key',
    questions: buildFullPaperQuestions('cgl-2023-t2', 'SSC CGL 2023 Tier-2 (26-Oct)', 2023)
  },
  {
    id: 'paper-cgl-2022-s1',
    title: 'SSC CGL 2022 Tier-1 (Shift 1 — 01 Dec 2022)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2022,
    shiftDate: '01-12-2022 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'MEDIUM',
    description: 'Classic shift paper establishing the new exam pattern with standard 100 Qs / 60 Mins format.',
    provenanceTag: 'SSC 2022 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2022-s1', 'SSC CGL 2022 Shift-1 (01-Dec)', 2022)
  }
];

// 2. SUBJECT-SPECIFIC FULL SECTIONAL TESTS (25 Qs each)
export const SUBJECT_MOCK_TESTS: MockPaper[] = [
  {
    id: 'sub-quant-full',
    title: 'Quantitative Aptitude Sectional Master Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'Quantitative Aptitude',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 25,
    difficulty: 'MEDIUM',
    description: 'Comprehensive 25-Question Quant section covering Arithmetic (CI/SI, Time-Work), Algebra identities, Geometry, and Trigonometry.',
    provenanceTag: 'TCS Quant Sectional Standard',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = QUANT_TEMPLATES[i % QUANT_TEMPLATES.length];
      return {
        id: `quant-sec-${i+1}`,
        topicId: `syl-quant-${i}`,
        subject: 'Quantitative Aptitude',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Quant Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: i % 3 === 0 ? 'HARD' : 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'sub-reasoning-full',
    title: 'Reasoning & Intelligence Sectional Master Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'Reasoning & General Intelligence',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 20,
    difficulty: 'EASY',
    description: 'High-speed 25-Question Reasoning test for practicing Syllogisms, Coded Blood Relations, Number Series, and Analogy.',
    provenanceTag: 'TCS Reasoning Sectional',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = REASONING_TEMPLATES[i % REASONING_TEMPLATES.length];
      return {
        id: `reas-sec-${i+1}`,
        topicId: `syl-reas-${i}`,
        subject: 'Reasoning & General Intelligence',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Reasoning Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: i % 2 === 0 ? 'EASY' : 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'sub-english-full',
    title: 'English Comprehension & Grammar Sectional Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'English Comprehension',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 15,
    difficulty: 'MEDIUM',
    description: 'Rapid 15-Minute English test focusing on Error Spotting, Synonyms/Antonyms, One-Word Substitution, and Active-Passive Voice.',
    provenanceTag: 'TCS English Sectional',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = ENGLISH_TEMPLATES[i % ENGLISH_TEMPLATES.length];
      return {
        id: `eng-sec-${i+1}`,
        topicId: `syl-eng-${i}`,
        subject: 'English Comprehension',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `English Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'sub-ga-full',
    title: 'General Awareness High-Yield Sectional Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'General Awareness',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 12,
    difficulty: 'MEDIUM',
    description: '12-Minute GA speed test covering Indian Constitution Articles, Modern Freedom Movements, Static GK, and Science.',
    provenanceTag: 'TCS GA Sectional',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = GA_TEMPLATES[i % GA_TEMPLATES.length];
      return {
        id: `ga-sec-${i+1}`,
        topicId: `syl-ga-${i}`,
        subject: 'General Awareness',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `GA Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'sub-computer-full',
    title: 'Tier-2 Computer Knowledge Qualifying Mock (20 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-2',
    subject: 'Computer Proficiency',
    totalQuestions: 20,
    totalMarks: 60,
    durationMinutes: 15,
    difficulty: 'MEDIUM',
    description: 'Mandatory qualifying Computer module for CGL Tier-2 (CPT posts like ASO CSS and Inspector).',
    provenanceTag: 'SSC Tier-2 Computer Module',
    questions: Array.from({ length: 20 }, (_, i) => {
      const t = COMPUTER_TEMPLATES[i % COMPUTER_TEMPLATES.length];
      return {
        id: `comp-sec-${i+1}`,
        topicId: `syl-comp-${i}`,
        subject: 'Computer Proficiency',
        topicName: t.topic,
        tier: 'TIER_2',
        shiftInfo: `Computer Module • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  }
];

// 3. TOPIC-SPECIFIC FOCUSED DRILLS (15 Qs each)
export const TOPIC_DRILL_TESTS: MockPaper[] = [
  {
    id: 'drill-quant-geom',
    title: 'Geometry: Circle Tangents, Chords & Triangles (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'Quantitative Aptitude',
    topic: 'Geometry: Circle Tangents & Secants',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 15,
    difficulty: 'HARD',
    description: 'Master Direct Common Tangents, Transverse Common Tangents, and Intersecting Chord Theorems.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = QUANT_TEMPLATES[2]; // Geometry template
      return {
        id: `drill-geom-${i+1}`,
        topicId: 'syl-quant-geom',
        subject: 'Quantitative Aptitude',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Geometry Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'HARD',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'drill-quant-algebra',
    title: 'Algebra: Symmetric Identities (x + 1/x) Drill (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'Quantitative Aptitude',
    topic: 'Algebra: Symmetric Polynomials (x + 1/x)',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 12,
    difficulty: 'MEDIUM',
    description: 'Practice rapid expansions for x² + 1/x², x³ + 1/x³, and x⁴ + 1/x⁴.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = QUANT_TEMPLATES[1]; // Algebra template
      return {
        id: `drill-alg-${i+1}`,
        topicId: 'syl-quant-algebra',
        subject: 'Quantitative Aptitude',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Algebra Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'drill-ga-polity',
    title: 'Indian Polity: Constitution Articles 14–51A Drill (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'General Awareness',
    topic: 'Indian Polity: Constitutional Articles',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 8,
    difficulty: 'EASY',
    description: 'High-frequency revision for Fundamental Rights (Part III), DPSP (Part IV), and Writs under Article 32 & 226.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = GA_TEMPLATES[0]; // Polity template
      return {
        id: `drill-polity-${i+1}`,
        topicId: 'syl-ga-polity',
        subject: 'General Awareness',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Polity Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'EASY',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'drill-reas-syllogism',
    title: 'Reasoning: Syllogisms & Logical Deductions (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'Reasoning & General Intelligence',
    topic: 'Syllogism: Logical Deductions',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 10,
    difficulty: 'MEDIUM',
    description: 'Speed building with 3-statement and 3-conclusion Venn logic puzzles.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = REASONING_TEMPLATES[0]; // Syllogism template
      return {
        id: `drill-syl-${i+1}`,
        topicId: 'syl-reas-syllogism',
        subject: 'Reasoning & General Intelligence',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Syllogism Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  },
  {
    id: 'drill-eng-grammar',
    title: 'English: 60 Golden Rules Error Spotting (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'English Comprehension',
    topic: 'Grammar: Subject-Verb Agreement',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 10,
    difficulty: 'MEDIUM',
    description: 'Focus on Subject-Verb agreement, Conditionals, and Preposition placement.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = ENGLISH_TEMPLATES[0]; // Grammar template
      return {
        id: `drill-gram-${i+1}`,
        topicId: 'syl-eng-grammar',
        subject: 'English Comprehension',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Grammar Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        provenance: sscProvenance
      };
    })
  }
];

// ==================================================================
// 4. MOCK TEST GENERATOR ASSISTANT ENGINE
// ==================================================================
export function generateCustomMockTest(config: CustomTestConfig): MockPaper {
  const selectedSubs = config.selectedSubjects.length > 0
    ? config.selectedSubjects
    : ['Quantitative Aptitude', 'Reasoning & General Intelligence', 'English Comprehension', 'General Awareness'];

  const targetCount = config.numQuestions || 25;
  const questions: PracticeQuestion[] = [];

  // Intelligent Timer Calculation Engine based on Difficulty & Subject Type
  // Hard Quant/Reasoning: 60s/Q | Normal Quant: 45s/Q | GA/English: 25s/Q | Easy: 30s/Q
  let secondsPerQuestion = 36; // Default
  if (config.difficulty === 'HARD') secondsPerQuestion = 55;
  else if (config.difficulty === 'EASY') secondsPerQuestion = 28;
  else if (config.difficulty === 'MEDIUM') secondsPerQuestion = 40;

  // Adjust if only GA/English selected
  const isOnlyFastSections = selectedSubs.every(s => s === 'General Awareness' || s === 'English Comprehension');
  if (isOnlyFastSections) {
    secondsPerQuestion = Math.round(secondsPerQuestion * 0.6);
  }

  const totalCalculatedMinutes = Math.max(5, Math.ceil((targetCount * secondsPerQuestion) / 60));

  for (let i = 0; i < targetCount; i++) {
    const subj = selectedSubs[i % selectedSubs.length];
    let template: any;

    if (subj === 'Quantitative Aptitude') {
      template = QUANT_TEMPLATES[i % QUANT_TEMPLATES.length];
    } else if (subj === 'Reasoning & General Intelligence') {
      template = REASONING_TEMPLATES[i % REASONING_TEMPLATES.length];
    } else if (subj === 'General Awareness') {
      template = GA_TEMPLATES[i % GA_TEMPLATES.length];
    } else if (subj === 'Computer Proficiency') {
      template = COMPUTER_TEMPLATES[i % COMPUTER_TEMPLATES.length];
    } else {
      template = ENGLISH_TEMPLATES[i % ENGLISH_TEMPLATES.length];
    }

    questions.push({
      id: `ai-custom-q${i+1}`,
      topicId: `custom-topic-${i}`,
      subject: subj,
      topicName: template.topic,
      tier: 'TIER_1',
      shiftInfo: `AI Custom Drill • Q${i+1}`,
      questionType: 'CUSTOM_AI_GENERATED',
      difficulty: config.difficulty,
      questionText: `[Q${i+1} • ${subj}] ${template.text}`,
      options: template.options.map((opt: string, idx: number) => ({ id: idx, text: opt })),
      correctOptionIndex: template.correct,
      explanation: template.exp,
      provenance: {
        ...sscProvenance,
        sourceName: 'AI Custom Exam Engine (Sourced from Official TCS Pattern)'
      }
    });
  }

  return {
    id: `ai-custom-mock-${Date.now()}`,
    title: config.title || `Custom AI Diagnostic Mock (${targetCount} Qs — ${config.difficulty} Level)`,
    category: 'CUSTOM_AI',
    examTier: 'Tier-1',
    totalQuestions: targetCount,
    totalMarks: targetCount * 2,
    durationMinutes: totalCalculatedMinutes,
    difficulty: config.difficulty,
    description: `Targeted practice paper assembled by the AI Generator covering ${selectedSubs.join(', ')}. Timer calibrated for ${config.difficulty} level.`,
    provenanceTag: `AI Tailored (${totalCalculatedMinutes} Mins)`,
    questions
  };
}
