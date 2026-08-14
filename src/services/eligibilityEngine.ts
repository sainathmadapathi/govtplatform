import { Exam, UserProfile, EligibilityDiagnostic, EligibilityRule, RuleGroup, PostRequirement } from '../types/exam';
import { calculateAge } from './profileUtils';

export function normalizeDegree(value: string): string {
  const normalized = value.toLowerCase().trim();
  if (normalized.includes('b.tech') || normalized.includes('b.e') || normalized.includes('engineering')) {
    return 'bachelor';
  }
  if (normalized.includes('b.sc') || normalized.includes('b.a') || normalized.includes('b.com') || normalized.includes('bachelor') || normalized.includes('graduation')) {
    return 'bachelor';
  }
  return normalized;
}

export function evaluateSingleRule(
  rule: EligibilityRule, 
  profile: UserProfile, 
  crucialCutoffDate: string = '2026-08-01'
): { pass: boolean; reason: string; clause: string } {
  const clause = rule.provenance.clauseNumber || 'Section 3.1';
  const candidateAge = calculateAge(profile.dateOfBirth, crucialCutoffDate);

  switch (rule.ruleType) {
    case 'AGE_MIN': {
      const minAge = Number(rule.ruleValue);
      const pass = candidateAge >= minAge;
      return {
        pass,
        reason: pass 
          ? `Calculated age of ${candidateAge} yrs (as of ${crucialCutoffDate}) satisfies minimum limit of ${minAge} yrs` 
          : `Calculated age of ${candidateAge} yrs (as of ${crucialCutoffDate}) is below minimum limit of ${minAge} yrs`,
        clause
      };
    }

    case 'AGE_MAX': {
      const maxAge = Number(rule.ruleValue);
      // Category age relaxation applied per category rule
      let relaxation = 0;
      if (profile.category === 'OBC') relaxation = 3;
      if (profile.category === 'SC' || profile.category === 'ST') relaxation = 5;
      if (profile.category === 'PwBD') relaxation = 10;
      
      const effectiveMaxAge = maxAge + relaxation;
      const pass = candidateAge <= effectiveMaxAge;
      
      return {
        pass,
        reason: pass
          ? `Calculated age of ${candidateAge} yrs (as of ${crucialCutoffDate}) satisfies maximum limit of ${effectiveMaxAge} yrs (${maxAge} base + ${relaxation} yrs ${profile.category} relaxation)`
          : `Calculated age of ${candidateAge} yrs (as of ${crucialCutoffDate}) exceeds maximum limit of ${effectiveMaxAge} yrs (${maxAge} base + ${relaxation} yrs ${profile.category} relaxation)`,
        clause
      };
    }

    case 'DOB_CUTOFF': {
      const cutoffDate = new Date(String(rule.ruleValue));
      const candidateDOB = new Date(profile.dateOfBirth);
      
      if (Number.isNaN(candidateDOB.getTime()) || Number.isNaN(cutoffDate.getTime())) {
        return { pass: false, reason: `Invalid Date of Birth provided`, clause };
      }

      const pass = candidateDOB <= cutoffDate;
      return {
        pass,
        reason: pass
          ? `Date of Birth (${profile.dateOfBirth}) satisfies the required cutoff date of ${rule.ruleValue}`
          : `Date of Birth (${profile.dateOfBirth}) exceeds the cutoff limit of ${rule.ruleValue}`,
        clause
      };
    }

    case 'DEGREE_REQUIRED': {
      const allowedDegrees = Array.isArray(rule.ruleValue) ? rule.ruleValue : [rule.ruleValue];
      const userDegreeNorm = normalizeDegree(profile.degree);
      
      const pass = allowedDegrees.some(deg => {
        const dNorm = normalizeDegree(String(deg));
        return userDegreeNorm === dNorm || userDegreeNorm.includes(dNorm) || dNorm.includes(userDegreeNorm);
      });
      
      return {
        pass,
        reason: pass
          ? `Degree (${profile.degree}) fulfills qualification criteria (${allowedDegrees.slice(0, 3).join(', ')})`
          : `Degree (${profile.degree}) does not fulfill required qualification (${allowedDegrees.slice(0, 3).join(', ')})`,
        clause
      };
    }

    case 'BRANCH_SPECIALIZATION': {
      if (rule.ruleValue === 'ANY' || rule.ruleValue === 'Any Branch') {
        return { pass: true, reason: `Any specialization branch is accepted`, clause };
      }
      const allowedBranches = Array.isArray(rule.ruleValue) ? rule.ruleValue : [rule.ruleValue];
      const userBranchNorm = profile.branch.toLowerCase().trim();
      
      const pass = allowedBranches.some(b => userBranchNorm.includes(String(b).toLowerCase()));
      return {
        pass,
        reason: pass
          ? `Specialization (${profile.branch}) matches post requirement`
          : `Specialization (${profile.branch}) does not meet branch constraint: ${allowedBranches.join(', ')}`,
        clause
      };
    }

    case 'PERCENTAGE_MIN': {
      const minPct = Number(rule.ruleValue);
      const pass = profile.percentage >= minPct;
      return {
        pass,
        reason: pass
          ? `Degree percentage (${profile.percentage}%) meets minimum cutoff of ${minPct}%`
          : `Degree percentage (${profile.percentage}%) is below required ${minPct}% cutoff`,
        clause
      };
    }

    case 'NATIONALITY': {
      const requiredNationalities = Array.isArray(rule.ruleValue) ? rule.ruleValue : [rule.ruleValue];
      const userNat = profile.nationality.toUpperCase().trim();
      
      const pass = requiredNationalities.some(nat => {
        const n = String(nat).toUpperCase().trim();
        return n.includes(userNat) || userNat.includes('INDIAN') || userNat === 'INDIA';
      });

      return {
        pass,
        reason: pass
          ? `Nationality (${profile.nationality}) satisfies requirement`
          : `Nationality (${profile.nationality}) does not satisfy required citizenship rule`,
        clause
      };
    }

    default:
      return { pass: true, reason: `Rule ${rule.ruleType} satisfied`, clause };
  }
}

export function evaluateRuleGroup(
  group: RuleGroup, 
  profile: UserProfile,
  crucialCutoffDate: string = '2026-08-01'
): { pass: boolean; reasons: string[]; clauses: string[] } {
  const reasons: string[] = [];
  const clauses: string[] = [];

  if (group.operator === 'AND') {
    let allPass = true;
    for (const rule of group.rules) {
      const res = evaluateSingleRule(rule, profile, crucialCutoffDate);
      reasons.push(res.reason);
      clauses.push(res.clause);
      if (!res.pass) allPass = false;
    }

    if (group.childGroups && group.childGroups.length > 0) {
      for (const childGroup of group.childGroups) {
        const childRes = evaluateRuleGroup(childGroup, profile, crucialCutoffDate);
        reasons.push(...childRes.reasons);
        clauses.push(...childRes.clauses);
        if (!childRes.pass) allPass = false;
      }
    }

    return { pass: allPass, reasons, clauses };
  } else {
    // OR group evaluation
    let anyPass = false;
    for (const rule of group.rules) {
      const res = evaluateSingleRule(rule, profile, crucialCutoffDate);
      reasons.push(res.reason);
      clauses.push(res.clause);
      if (res.pass) anyPass = true;
    }

    if (group.childGroups && group.childGroups.length > 0) {
      for (const childGroup of group.childGroups) {
        const childRes = evaluateRuleGroup(childGroup, profile, crucialCutoffDate);
        reasons.push(...childRes.reasons);
        clauses.push(...childRes.clauses);
        if (childRes.pass) anyPass = true;
      }
    }

    return { pass: anyPass, reasons, clauses };
  }
}

export function evaluateCandidateEligibility(exam: Exam, profile: UserProfile): EligibilityDiagnostic {
  // Crucial cutoff date for age determination (e.g. '2026-08-01')
  const crucialCutoffDate = '2026-08-01';

  // Global exam rule evaluation
  const globalEval = evaluateRuleGroup(exam.globalRuleGroup, profile, crucialCutoffDate);

  // Post-specific evaluation
  const postVerdicts = exam.posts.map((post: PostRequirement) => {
    let isEligible = globalEval.pass;
    let reason = globalEval.pass ? `Fulfills all general graduate eligibility requirements` : globalEval.reasons.find(r => r.includes('exceeds') || r.includes('below') || r.includes('does not')) || globalEval.reasons[0];
    let clause = post.provenance.clauseNumber || 'Clause 3.1';

    if (post.id === 'post-jso') {
      // Step 11: Complex JSO post rule requires manual 12th Standard Math/Stat verification
      isEligible = globalEval.pass; 
      reason = globalEval.pass 
        ? `General degree matched. Requires 60% in Math at 12th Std or Statistics subject (Requires candidate self-verification)` 
        : (globalEval.reasons.find(r => r.includes('exceeds') || r.includes('below') || r.includes('does not')) || globalEval.reasons[0]);
      clause = post.provenance.clauseNumber || 'Section 3.1, Clause 3(b)';
    } else if (post.ruleGroup) {
      const postEval = evaluateRuleGroup(post.ruleGroup, profile, crucialCutoffDate);
      isEligible = globalEval.pass && postEval.pass;
      reason = !globalEval.pass ? (globalEval.reasons.find(r => r.includes('exceeds') || r.includes('below') || r.includes('does not')) || globalEval.reasons[0]) : (postEval.reasons[0] || 'Post requirements satisfied');
    }

    return {
      postName: post.postName,
      department: post.department,
      eligible: isEligible,
      reason,
      clause
    };
  });

  const eligiblePostsCount = postVerdicts.filter(p => p.eligible).length;
  const isOverallEligible = eligiblePostsCount > 0;
  const isFullyEligible = eligiblePostsCount === postVerdicts.length;

  const candidateAge = calculateAge(profile.dateOfBirth, crucialCutoffDate);

  // Step 12: Eligibility status logic
  const status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE' = isFullyEligible
    ? 'ELIGIBLE'
    : (isOverallEligible ? 'CONDITIONAL' : 'INELIGIBLE');

  const uniqueClauses = Array.from(new Set(globalEval.clauses));

  const plainEnglishExplanation = isOverallEligible
    ? `Based on your Date of Birth (${profile.dateOfBirth}, calculated age ${candidateAge} yrs as of ${crucialCutoffDate}), ${profile.degree} in ${profile.branch}, ${profile.category} category, and ${profile.nationality} nationality: You meet the cutoff criteria for ${eligiblePostsCount} out of ${postVerdicts.length} posts under ${exam.title}.`
    : `Based on your Date of Birth (${profile.dateOfBirth}, calculated age ${candidateAge} yrs as of ${crucialCutoffDate}), ${profile.degree} in ${profile.branch}, ${profile.category} category, and ${profile.nationality} nationality: You do not currently meet the eligibility criteria for ${exam.title}. Review the diagnostic breakdown below.`;

  return {
    isEligible: isOverallEligible,
    status,
    legalClauses: uniqueClauses,
    plainEnglishExplanation,
    postVerdicts
  };
}
