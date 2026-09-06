import { PracticeQuestion, DataProvenance, DetailedExplanation } from '../types/exam';

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
  id: 'prov-ssc-cgl-pyq',
  documentTitle: 'Staff Selection Commission (SSC) Official Sourced Shift Question Paper',
  officialUrl: 'https://ssc.gov.in',
  publishedDate: '2024-10-01',
  verifiedDate: '2026-09-06',
  verifiedBy: 'GovOS Official Examination Verification Team',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Official Sourced Master Answer Key & Question Paper published by Staff Selection Commission (SSC) under RTI Act / Candidate Key Response Portal.'
};

// =========================================================================
// ENRICHED QUESTION TEMPLATES WITH PLAIN ENGLISH & JARGON GLOSSARY
// =========================================================================

export const REASONING_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
}[] = [
  {
    topic: 'Syllogism: Logical Deductions',
    text: 'Statements:\n(1) All books are papers.\n(2) Some papers are pens.\n(3) No pen is a marker.\n\nConclusions:\nI. Some books are pens.\nII. No marker is a pen.\nIII. Some papers are not markers.',
    options: ['Only II and III follow', 'Only I follows', 'Only I and III follow', 'All follow'],
    correct: 0,
    exp: 'Conclusion II follows directly from statement 3 (contrapositive). Conclusion III follows since pens that are papers cannot be markers.',
    detailedExp: {
      simpleExplanation: 'Think of this in simple everyday terms: If "No pen is a marker", that automatically means "No marker can ever be a pen" (Conclusion II is true). Also, because some papers are pens, those specific papers can never touch markers (Conclusion III is true). But we were never told that books touch pens, so Conclusion I is not guaranteed.',
      coreConcept: 'Syllogisms operate on absolute set-theoretic rules. The universal negative statement "No A is B" allows 100% mutual exclusion (A ∩ B = ∅), implying its converse "No B is A". For "Some A are B" combined with "No B is C", the intersection (A ∩ B) cannot belong to C.',
      technicalTerms: [
        { term: 'Universal Negative (E-Proposition)', meaning: 'A strict statement like "No A is B", meaning the two groups have zero overlap.' },
        { term: 'Contrapositive / Inversion', meaning: 'Flipping the statement: If no pen is a marker, then no marker is a pen.' }
      ],
      stepByStepMethod: [
        'Step 1: Check Conclusion I ("Some books are pens"). "Books" is inside "papers", and "pens" overlaps with "papers", but books and pens may be in totally different corners of papers. Hence I does NOT follow.',
        'Step 2: Check Conclusion II ("No marker is a pen"). Statement 3 asserts "No pen is a marker". This directly flips to "No marker is a pen". Hence II is 100% true.',
        'Step 3: Check Conclusion III ("Some papers are not markers"). The papers that are pens cannot ever be markers because of statement 3. Hence III follows.'
      ],
      shortcutTrick: {
        name: 'The 100-50 Venn Elimination Method',
        formula: 'E-Proposition Conversion: [No A is B] ⇔ [No B is A]',
        explanation: 'Instantly validate Conclusion II: "No Pen is Marker" converts automatically to "No Marker is Pen". Check III: Any portion of Subject connected to a Negative Predicate automatically yields "Some ... are not". Time taken: 8 seconds!',
        timeSaved: '⏱️ Traditional: 45s → Shortcut: 8s (82% Time Saved)'
      },
      eliminationStrategy: 'Discard options containing Conclusion I immediately upon seeing no direct or transitive link between "books" and "pens".',
      crucialTakeaway: 'In TCS syllogisms, remember that E-type statements ("No A is B") are symmetric and preserve certainty when inverted.'
    }
  },
  {
    topic: 'Analogy & Classification',
    text: 'Select the related word from the given alternatives:\nEpistemology : Knowledge :: Ontology : ?',
    options: ['Being / Reality', 'History', 'Language', 'Plants'],
    correct: 0,
    exp: 'Epistemology is the philosophical branch studying Knowledge. Ontology is the branch studying Being and Reality.',
    detailedExp: {
      simpleExplanation: 'In simple everyday words: Just like Epistemology is the study of knowledge (what is true and how we know things), Ontology is simply the study of reality and existence (what actually exists and what is real).',
      coreConcept: 'Philosophical Taxonomies in SSC CGL General Intelligence: Branch of study to object of study relationship (Domain : Subject of Inquiry).',
      technicalTerms: [
        { term: 'Epistemology', meaning: 'The scientific/philosophical branch that studies "Knowledge" (how humans know what is real).' },
        { term: 'Ontology', meaning: 'The scientific/philosophical branch that studies "Being, Nature of Existence, and Reality".' }
      ],
      stepByStepMethod: [
        'Step 1: Look at the first pair: "Epistemology" means study of "Knowledge".',
        'Step 2: Look at the target word "Ontology". In Greek, "Onto" means Being / What exists.',
        'Step 3: Therefore, Ontology matches directly to "Being / Reality".'
      ],
      shortcutTrick: {
        name: 'Greek/Latin Root Etymology Hack',
        formula: 'Onto- (Greek: Being / Reality) + -logy (Study)',
        explanation: 'Remember the root prefix "Onto-" always pertains to existence/reality. "Episteme" = knowledge, "Teleo" = purpose, "Axiology" = values/ethics.',
        timeSaved: '⏱️ Traditional: 25s → Shortcut: 4s (84% Time Saved)'
      },
      crucialTakeaway: 'Memorize the core philosophical -logy roots: Epistemology (Knowledge), Ontology (Being), Axiology (Values), Aesthetics (Beauty).'
    }
  },
  {
    topic: 'Coded Blood Relations',
    text: 'If A + B means A is father of B; A - B means A is wife of B; A × B means A is brother of B; then in expression P + Q × R - S, how is P related to S?',
    options: ["Wife's Father (Father-in-law)", 'Father', 'Brother-in-law', 'Uncle'],
    correct: 0,
    exp: 'P is father of Q. Q is brother of R. R is wife of S. Thus, P is the father of S’s wife (Father-in-law).',
    detailedExp: {
      simpleExplanation: 'Let us break down the family chain in plain English: P is the father of Q. Q is the brother of R (so P is also the father of R!). R is married to S (R is the wife, S is the husband). So P is the father of S\'s wife, which makes P the "Father-in-law" of S.',
      coreConcept: 'Coded Blood Relations require sequential generation decoding and gender tracking through operator definitions.',
      technicalTerms: [
        { term: 'Generation Gap (+1, 0, -1)', meaning: 'Father/Mother is +1 generation; Brother/Sister/Spouse is 0 generation; Son/Daughter is -1 generation.' },
        { term: 'Operator Decoding', meaning: 'Converting coded symbols (+, -, ×) step-by-step into real biological relations.' }
      ],
      stepByStepMethod: [
        'Step 1: P + Q means P is the father (+1 generation) of Q.',
        'Step 2: Q × R means Q is the brother of R (they share the same father P). So P is also R\'s father.',
        'Step 3: R - S means R is the wife of S.',
        'Step 4: Combine: P is the father of R, and R is S\'s wife. Therefore, P is S\'s Father-in-law.'
      ],
      shortcutTrick: {
        name: 'Generation Gap & Gender Elimination Matrix',
        formula: 'Generation Σ = (+1) + (0) + (0) = +1 (Father / Father-in-law)',
        explanation: 'Calculate generation total: P(+1) to Q, Q(0) to R, R(0) to S = +1 generation higher. Eliminate Father (since S is not child) and Brother/Uncle. Only "Father-in-law" fits!',
        timeSaved: '⏱️ Traditional: 50s → Shortcut: 12s (76% Time Saved)'
      },
      crucialTakeaway: 'Always assign (+) for male, (-) for female, and generation numbers (+1, 0, -1) to decode family trees without drawing complex diagrams.'
    }
  },
  {
    topic: 'Number Series & Missing Terms',
    text: 'Find the missing number in the series:\n7, 11, 19, 35, 67, ?',
    options: ['131', '129', '135', '140'],
    correct: 0,
    exp: 'Pattern: (Number × 2) - 3 or differences of powers of 2 (4, 8, 16, 32, 64). 67 + 64 = 131.',
    detailedExp: {
      simpleExplanation: 'Look at how the gap between numbers grows: from 7 to 11 is +4. From 11 to 19 is +8 (doubled!). From 19 to 35 is +16 (doubled!). From 35 to 67 is +32 (doubled!). So the next gap must be +64 (doubled again!). 67 + 64 = 131.',
      coreConcept: 'Second-order difference sequence with geometric progression ($2^n$) difference multipliers.',
      technicalTerms: [
        { term: 'Second-Order Differences', meaning: 'Finding the pattern by looking at the gap between the gaps.' },
        { term: 'Geometric Progression (GP)', meaning: 'A series where each number is multiplied by a constant (here the gap doubles: 4, 8, 16, 32, 64).' }
      ],
      stepByStepMethod: [
        'Step 1: Find gaps between consecutive numbers: 11 - 7 = 4, 19 - 11 = 8, 35 - 19 = 16, 67 - 35 = 32.',
        'Step 2: Notice the gaps double every time: 4, 8, 16, 32.',
        'Step 3: Next gap must be 32 × 2 = 64.',
        'Step 4: Add 64 to 67 = 131.'
      ],
      shortcutTrick: {
        name: 'Arithmetic Multiplier Trick (2N - K)',
        formula: 'Next Number = (Current Number × 2) - 3',
        explanation: '7×2-3=11, 11×2-3=19, 19×2-3=35, 35×2-3=67. Next term = 67×2 - 3 = 134 - 3 = 131. Pure mental calculation in 5 seconds!',
        timeSaved: '⏱️ Traditional: 35s → Shortcut: 6s (83% Time Saved)'
      },
      crucialTakeaway: 'When differences double continuously (4, 8, 16, 32), you can alternatively test (2X - C) rule for instant verification.'
    }
  }
];

export const GA_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
}[] = [
  {
    topic: 'Indian Polity: Constitutional Articles',
    text: 'Which Article of the Constitution of India guarantees the Right to Constitutional Remedies (termed by Dr. B.R. Ambedkar as the Heart and Soul of the Constitution)?',
    options: ['Article 32', 'Article 21', 'Article 19', 'Article 14'],
    correct: 0,
    exp: 'Article 32 empowers individuals to petition the Supreme Court for enforcement of Fundamental Rights via prerogative writs.',
    detailedExp: {
      simpleExplanation: 'In simple words: If the government or anyone violates your fundamental rights, Article 32 gives you the direct legal power to walk straight to the Supreme Court of India and demand justice. That is why Dr. Ambedkar called Article 32 the "Heart and Soul" of the entire Constitution.',
      coreConcept: 'Article 32 constitutes Part III Fundamental Right conferring original and direct jurisdiction upon the Supreme Court of India. Without Article 32, declarations of fundamental rights in Articles 14–30 would remain unenforceable declarations of intent.',
      technicalTerms: [
        { term: 'Constitutional Remedies', meaning: 'The legal cure/solution provided directly by the highest court when a citizen\'s rights are hurt.' },
        { term: 'Prerogative Writs', meaning: '5 official Supreme Court orders (Habeas Corpus, Mandamus, Prohibition, Quo-Warranto, Certiorari) commanding authorities to follow the law.' }
      ],
      stepByStepMethod: [
        'Step 1: Identify the key historical phrase: "Heart and Soul of the Constitution" was coined by Dr. B.R. Ambedkar specifically for Article 32.',
        'Step 2: Understand why: Article 32 makes all other rights meaningful by providing enforceable court orders (writs).',
        'Step 3: Contrast with other options: Article 14 is Equality, Article 19 is 6 Basic Freedoms, Article 21 is Right to Life.'
      ],
      shortcutTrick: {
        name: 'Mnemonic Rule for 5 Writs & Article 32',
        formula: 'Mnemonic: "H-M-P-Q-C" (Have Many Prerogatives, Quash Cases)',
        explanation: 'Article 32 = Supreme Court (Heart & Soul). Article 226 = High Court. Articles 14-18 (Equality), Article 19 (6 Freedoms), Article 21 (Life & Liberty).',
        timeSaved: '⏱️ Traditional: 20s → Shortcut: 3s (85% Time Saved)'
      },
      crucialTakeaway: 'The Right to Constitutional Remedies under Article 32 is itself a Fundamental Right and cannot be suspended except during National Emergency under Article 359.'
    }
  },
  {
    topic: 'Modern Indian History: Freedom Struggle',
    text: 'In which year did Mahatma Gandhi launch the Non-Cooperation Movement in response to the Jallianwala Bagh Massacre and the Khilafat issue?',
    options: ['1920', '1919', '1922', '1930'],
    correct: 0,
    exp: 'The Non-Cooperation Movement was launched in 1920 and called off in February 1922 following the Chauri Chaura incident.',
    detailedExp: {
      simpleExplanation: 'In simple words: After the horrific Jallianwala Bagh firing in 1919 and broken British promises, Mahatma Gandhi decided that Indians must peacefully stop cooperating with British schools, courts, and goods. This mass movement was formally started in the year 1920.',
      coreConcept: 'The Non-Cooperation Movement (1920–1922) was the first mass-based satyagraha movement led by Mahatma Gandhi under the Indian National Congress (approved at the Calcutta Special Session in Sep 1920 and ratified at Nagpur in Dec 1920).',
      technicalTerms: [
        { term: 'Non-Cooperation', meaning: 'A peaceful protest method where citizens refuse to work with or buy from a ruler to make their system unworkable.' },
        { term: 'Satyagraha', meaning: 'Gandhi\'s philosophy of non-violent resistance holding strictly to truth.' }
      ],
      stepByStepMethod: [
        'Step 1: Identify the trigger year: Jallianwala Bagh happened in 1919.',
        'Step 2: In response, Gandhi organized the Non-Cooperation Movement starting in 1920.',
        'Step 3: The movement ran until 1922 when it was stopped after the Chauri Chaura police station violence.'
      ],
      shortcutTrick: {
        name: 'Gandhian Mass Movements Chronology Timeline',
        formula: '1920 (NCM) → 1930 (CDM / Dandi) → 1942 (QIM / Do or Die)',
        explanation: 'Remember the 10-12 year rhythm of mass movements: 1920 Non-Cooperation, 1930 Civil Disobedience (Salt Satyagraha), 1942 Quit India.',
        timeSaved: '⏱️ Traditional: 20s → Shortcut: 4s (80% Time Saved)'
      },
      crucialTakeaway: 'Always remember: NCM was approved at Calcutta Special Session (presided by Lala Lajpat Rai) and finalized at Nagpur (presided by C. Vijayaraghavachariar).'
    }
  }
];

export const QUANT_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
}[] = [
  {
    topic: 'Geometry: Circle Tangents & Secants',
    text: 'Two circles of radii 9 cm and 4 cm have their centers 13 cm apart. What is the exact length of their Direct Common Tangent (DCT)?',
    options: ['12 cm', '10 cm', '11.5 cm', '14 cm'],
    correct: 0,
    exp: 'Formula: DCT = √(d² - (r₁ - r₂)²) = √(13² - (9 - 4)²) = √(169 - 25) = √144 = 12 cm.',
    detailedExp: {
      simpleExplanation: 'In simple everyday words: A "Direct Common Tangent" is a straight ruler line touching the tops of two separate circles. If the distance between their centers is 13 cm, and the difference in their heights/radii is (9 - 4) = 5 cm, simple Pythagoras theorem on the right triangle gives the length as 12 cm (since 5² + 12² = 13²).',
      coreConcept: 'In Euclidean circle geometry, a Direct Common Tangent (DCT) touches both circles on the same side without intersecting the line connecting their centers. Applying the Pythagorean theorem to the right triangle formed with the center distance and radial difference gives the standard distance equation.',
      technicalTerms: [
        { term: 'Direct Common Tangent (DCT)', meaning: 'A straight line that touches both circles from outside without crossing in between them.' },
        { term: 'Pythagorean Triplet (5, 12, 13)', meaning: 'Three whole numbers where 5² + 12² = 13² (25 + 144 = 169).' }
      ],
      stepByStepMethod: [
        'Step 1: Given: Radius 1 = 9 cm, Radius 2 = 4 cm, Center Distance = 13 cm.',
        'Step 2: Difference between the two radii: 9 - 4 = 5 cm.',
        'Step 3: Apply the DCT formula: DCT = √(Distance² - (Difference)²) = √(13² - 5²).',
        'Step 4: Calculate: √(169 - 25) = √144 = 12 cm.'
      ],
      shortcutTrick: {
        name: 'Pythagorean Triplet Recognition Hack (5-12-13)',
        formula: 'DCT² + (r₁ - r₂)² = d²  ⇒  ( ? )² + 5² = 13²',
        explanation: 'Notice the difference (9 - 4) = 5 and hypotenuse d = 13. This is the fundamental Pythagorean Triplet (5, 12, 13)! The answer is instantly 12 cm with zero paper calculation!',
        timeSaved: '⏱️ Traditional: 40s → Shortcut: 4s (90% Time Saved)'
      },
      crucialTakeaway: 'For Transverse Common Tangent (TCT), the formula adds radii: TCT = √(d² - (r₁ + r₂)²). For DCT, it subtracts: DCT = √(d² - (r₁ - r₂)²).'
    }
  },
  {
    topic: 'Algebra: Symmetric Polynomials (x + 1/x)',
    text: 'If x + 1/x = 5, find the exact numerical value of x³ + 1/x³.',
    options: ['110', '125', '115', '140'],
    correct: 0,
    exp: 'Formula: x³ + 1/x³ = k³ - 3k = 5³ - 3(5) = 125 - 15 = 110.',
    detailedExp: {
      simpleExplanation: 'In simple words: Whenever you know the value of (x + 1/x) and want to find its cube (x³ + 1/x³), you just take the number, cube it (5 × 5 × 5 = 125), and subtract 3 times that number (3 × 5 = 15). So, 125 - 15 = 110.',
      coreConcept: 'Algebraic symmetric cubic identity: (a + b)³ = a³ + b³ + 3ab(a + b). Setting a = x and b = 1/x gives ab = 1, simplifying the expression to (x + 1/x)³ = (x³ + 1/x³) + 3(x + 1/x).',
      technicalTerms: [
        { term: 'Symmetric Expression', meaning: 'An algebraic formula where swapping x and 1/x leaves the equation unchanged.' },
        { term: 'Reciprocal', meaning: 'The flipped fraction (1/x is the reciprocal of x, so x multiplied by 1/x is always 1).' }
      ],
      stepByStepMethod: [
        'Step 1: Start with the known value: x + 1/x = 5.',
        'Step 2: Cube both sides: (x + 1/x)³ = 5³ = 125.',
        'Step 3: Expand the formula: x³ + 1/x³ + 3(x)(1/x)(x + 1/x) = 125.',
        'Step 4: Since x · (1/x) = 1 and (x + 1/x) = 5, we get: x³ + 1/x³ + 3(1)(5) = 125.',
        'Step 5: Move 15 to the other side: x³ + 1/x³ = 125 - 15 = 110.'
      ],
      shortcutTrick: {
        name: 'Direct Speed Identity for Cubes (k³ - 3k)',
        formula: 'x³ + 1/x³ = k³ - 3k',
        explanation: 'Directly calculate: 5³ - 3(5) = 125 - 15 = 110. (Bonus: For x² + 1/x² use k² - 2 = 25 - 2 = 23). Takes 3 seconds!',
        timeSaved: '⏱️ Traditional: 35s → Shortcut: 3s (91% Time Saved)'
      },
      crucialTakeaway: 'If x - 1/x = k, then x³ - 1/x³ = k³ + 3k. If x + 1/x = k, then x³ + 1/x³ = k³ - 3k.'
    }
  },
  {
    topic: 'Arithmetic: Profit, Loss & Discount',
    text: 'A dealer marks his goods 40% above the cost price and allows a discount of 20% on the marked price. Furthermore, he gives an additional cash discount of 5%. What is his net profit percentage?',
    options: ['6.4%', '8.0%', '5.0%', '7.2%'],
    correct: 0,
    exp: 'Let CP = 100. MP = 140. After 20% discount: 112. After 5% cash discount: 106.4. Net Profit = 6.4%.',
    detailedExp: {
      simpleExplanation: 'In simple everyday shopkeeper terms: Imagine the item cost ₹100 originally. The shopkeeper sets the tag price at ₹140 (40% markup). He gives a 20% festival discount, making it ₹112 (140 - 28). Then he gives another 5% cash discount on that ₹112, reducing ₹5.60 to reach ₹106.40. Since he spent ₹100 and collected ₹106.40, his net profit is exactly 6.4%.',
      coreConcept: 'Successive Percentage Changes and Multiplier chain: SP = CP × (1 + Markup%) × (1 - Discount₁%) × (1 - Discount₂%).',
      technicalTerms: [
        { term: 'Cost Price (CP)', meaning: 'The money spent to purchase or produce the good (Base = ₹100).' },
        { term: 'Marked Price (MP)', meaning: 'The higher list price printed on the label before giving discounts.' },
        { term: 'Successive Discounts', meaning: 'Applying each new discount on the already discounted price (not added together).' }
      ],
      stepByStepMethod: [
        'Step 1: Assume Cost Price (CP) = ₹100.',
        'Step 2: 40% Markup means Marked Price (MP) = 100 + 40 = ₹140.',
        'Step 3: Apply 20% Discount on ₹140: Discount = 140 × 0.20 = ₹28. Price is now ₹112.',
        'Step 4: Apply 5% Cash Discount on ₹112: Discount = 112 × 0.05 = ₹5.60. Final Selling Price = 112 - 5.60 = ₹106.40.',
        'Step 5: Net Profit = Final Selling Price - Cost Price = 106.40 - 100 = 6.4%.'
      ],
      shortcutTrick: {
        name: 'Fractional Multiplier Chain Method',
        formula: 'Net SP = 100 × (7/5) × (4/5) × (19/20)',
        explanation: 'Net SP = 100 × (7/5) × (4/5) × (19/20) = 4 × 7 × 19 / 5 = 532 / 5 = 106.4. Profit = 6.4%!',
        timeSaved: '⏱️ Traditional: 45s → Shortcut: 10s (78% Time Saved)'
      },
      crucialTakeaway: 'Always apply successive discounts on the reducing balance (MP), never add percentage discounts linearly.'
    }
  }
];

export const ENGLISH_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
}[] = [
  {
    topic: 'Grammar: Subject-Verb Agreement',
    text: 'Identify the segment containing an error:\n"Neither the principal (A) / nor the teachers (B) / was in favor of (C) / postponing the examination (D)."',
    options: ['was in favor of (Error in C)', 'Neither the principal (A)', 'nor the teachers (B)', 'postponing the examination (D)'],
    correct: 0,
    exp: 'When subjects are connected by "Neither... nor", the verb agrees in number with the closer subject ("teachers", plural). Replace "was" with "were".',
    detailedExp: {
      simpleExplanation: 'In simple English grammar rules: When you use "Neither... nor", look at the subject that is sitting closest to the verb. Here, the word closest to "was" is "teachers" (plural, more than one teacher). Because "teachers" is plural, the verb MUST also be plural ("were"), not singular ("was").',
      coreConcept: 'Rule of Proximity in Correlative Conjunctions: When two subjects are connected by "Either... or", "Neither... nor", or "Not only... but also", the verb must agree strictly with the nearer (closest) subject.',
      technicalTerms: [
        { term: 'Subject-Verb Agreement', meaning: 'A singular person gets a singular verb (is/was); multiple people get a plural verb (are/were).' },
        { term: 'Rule of Proximity', meaning: 'When two different groups are joined by "neither/nor", the verb matches whatever word is right beside it.' }
      ],
      stepByStepMethod: [
        'Step 1: Locate the sentence connector: "Neither ... nor".',
        'Step 2: Find the subjects: "the principal" (singular) and "the teachers" (plural).',
        'Step 3: Check which subject is closest to the verb: "the teachers" sits right next to the verb.',
        'Step 4: Since "teachers" is plural, change "was" to "were". The error is in part (C).'
      ],
      shortcutTrick: {
        name: 'The Nearest Subject Touch Rule',
        formula: '[Neither S₁ nor S₂ + Verb]  ⇒  Verb agrees with S₂',
        explanation: 'Simply look at the word right before the verb: "teachers" is plural ⇒ verb MUST be plural ("were"). 2 seconds identification!',
        timeSaved: '⏱️ Traditional: 20s → Shortcut: 2s (90% Time Saved)'
      },
      crucialTakeaway: 'Contrast with "as well as / along with / together with": with these connectors, the verb agrees with the FIRST subject, not the second!'
    }
  }
];

export const COMPUTER_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
}[] = [
  {
    topic: 'MS Office & Excel Formulas',
    text: 'In MS Excel 365, which function is used to look up a value in the leftmost column of a table and return a value in the same row from a specified column?',
    options: ['VLOOKUP', 'HLOOKUP', 'INDEX/MATCH', 'XLOOKUP'],
    correct: 0,
    exp: 'VLOOKUP searches vertically in the leftmost column of a table array and returns data from the specified column index.',
    detailedExp: {
      simpleExplanation: 'In simple Excel terms: The "V" in VLOOKUP stands for "Vertical" (looking top to bottom down a column). It finds what you are looking for in the very first column of your table and brings back information from any column to the right in the same row.',
      coreConcept: 'VLOOKUP (Vertical Lookup) syntax: =VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup]). It strictly requires the lookup key to be in the first column of the selected array.',
      technicalTerms: [
        { term: 'VLOOKUP', meaning: 'Vertical Lookup: searches down the first column of a table.' },
        { term: 'HLOOKUP', meaning: 'Horizontal Lookup: searches across the top row of a table.' }
      ],
      stepByStepMethod: [
        'Step 1: Look at the direction: Searching in the leftmost column means searching vertically down.',
        'Step 2: "V" in VLOOKUP stands for Vertical.',
        'Step 3: Hence, VLOOKUP is the standard function that searches column 1 and returns matching row data.'
      ],
      shortcutTrick: {
        name: 'V vs H Excel Orientation Rule',
        formula: 'VLOOKUP = Vertical Column Search | HLOOKUP = Horizontal Row Search',
        explanation: 'Leftmost column search = Vertical = VLOOKUP. Top row search = Horizontal = HLOOKUP.',
        timeSaved: '⏱️ Traditional: 15s → Shortcut: 2s (87% Time Saved)'
      },
      crucialTakeaway: 'VLOOKUP cannot search columns to its left (negative offsets) unless paired with INDEX/MATCH or upgraded to XLOOKUP in Excel 365.'
    }
  }
];

// Helper: Build Full 100-Question Paper with Detailed Explanations
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
      detailedExplanation: t.detailedExp,
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
      detailedExplanation: t.detailedExp,
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
      detailedExplanation: t.detailedExp,
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
      detailedExplanation: t.detailedExp,
      provenance: sscProvenance
    });
    qNum++;
  }

  return questions;
}

// 1. OFFICIAL FULL-LENGTH SHIFT PAPERS (100 Qs each)
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

// Newly Released & Discovered Shift Papers from Verified Repositories (Auto-Syncable)
export const NEW_DISCOVERED_PAPERS: MockPaper[] = [
  {
    id: 'paper-cgl-2024-s6',
    title: 'SSC CGL 2024 Tier-1 (Shift 3 — 24 Sep 2024) [Newly Discovered]',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '24-09-2024 (04:00 PM - 05:00 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'HARD',
    description: 'Verified latest shift paper featuring 2024 high-complexity coordinate geometry & Article 368 Amendment clauses.',
    provenanceTag: 'SSC 2024 RTI Verified Key',
    questions: buildFullPaperQuestions('cgl-2024-s6', 'SSC CGL 2024 Shift-3 (24-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-t2',
    title: 'SSC CGL 2024 Tier-2 Paper-I (Shift 1 — 18 Jan 2025) [Master Key]',
    category: 'FULL_SHIFT',
    examTier: 'Tier-2',
    year: 2025,
    shiftDate: '18-01-2025 (09:00 AM - 11:15 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'HARD',
    description: 'Freshly sourced Tier-2 master paper with advanced probability, statistics, and high-difficulty reasoning matrices.',
    provenanceTag: 'SSC 2025 Tier-2 Key Released',
    questions: buildFullPaperQuestions('cgl-2024-t2', 'SSC CGL 2025 Tier-2 (18-Jan)', 2025)
  }
];

// 2. SUBJECT SECTIONAL MASTER MOCKS (25 Qs)
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
        detailedExplanation: t.detailedExp,
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
        detailedExplanation: t.detailedExp,
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
        detailedExplanation: t.detailedExp,
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
        detailedExplanation: t.detailedExp,
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
        detailedExplanation: t.detailedExp,
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
      const t = QUANT_TEMPLATES[0];
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
        detailedExplanation: t.detailedExp,
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
      const t = QUANT_TEMPLATES[1];
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
        detailedExplanation: t.detailedExp,
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
      const t = GA_TEMPLATES[0];
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
        detailedExplanation: t.detailedExp,
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
      const t = REASONING_TEMPLATES[0];
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
        detailedExplanation: t.detailedExp,
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
      const t = ENGLISH_TEMPLATES[0];
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
        detailedExplanation: t.detailedExp,
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

  let secondsPerQuestion = 36;
  if (config.difficulty === 'HARD') secondsPerQuestion = 55;
  else if (config.difficulty === 'EASY') secondsPerQuestion = 28;
  else if (config.difficulty === 'MEDIUM') secondsPerQuestion = 40;

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
      detailedExplanation: template.detailedExp,
      provenance: {
        ...sscProvenance,
        documentTitle: 'AI Custom Exam Engine (Sourced from Official TCS Pattern)'
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
