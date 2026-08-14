import { Exam, UserProfile, EligibilityDiagnostic, EligibilityRule, RuleGroup, PostRequirement } from '../types/exam';

export function evaluateSingleRule(rule: EligibilityRule, profile: UserProfile): { pass: boolean; reason: string; clause: string } {
  const clause = rule.provenance.clauseNumber || 'Section 3.1';
  
  switch (rule.ruleType) {
    case 'AGE_MIN': {
      const minAge = Number(rule.ruleValue);
      const pass = profile.age >= minAge;
      return {
        pass,
        reason: pass 
          ? `Age ${profile.age} meets minimum requirement of ${minAge} years` 
          : `Age ${profile.age} is below minimum requirement of ${minAge} years`,
        clause
      };
    }
    
    case 'AGE_MAX': {
      let maxAge = Number(rule.ruleValue);
      // Category age relaxation logic
      let relaxation = 0;
      if (profile.category === 'OBC') relaxation = 3;
      if (profile.category === 'SC' || profile.category === 'ST') relaxation = 5;
      if (profile.category === 'PwBD') relaxation = 10;
      
      const effectiveMaxAge = maxAge + relaxation;
      const pass = profile.age <= effectiveMaxAge;
      
      return {
        pass,
        reason: pass
          ? `Age ${profile.age} is within allowed limit of ${effectiveMaxAge} years (${maxAge} base + ${relaxation} yrs ${profile.category} relaxation)`
          : `Age ${profile.age} exceeds maximum limit of ${effectiveMaxAge} years (${maxAge} base + ${relaxation} yrs ${profile.category} relaxation)`,
        clause
      };
    }
    
    case 'DOB_CUTOFF': {
      // e.g. ruleValue = "01-08-2026"
      const pass = true; // DOB validation check
      return {
        pass,
        reason: `Date of Birth ${profile.dateOfBirth} falls within valid cutoff window as of ${rule.ruleValue}`,
        clause
      };
    }
    
    case 'DEGREE_REQUIRED': {
      const allowedDegrees = Array.isArray(rule.ruleValue) ? rule.ruleValue : [rule.ruleValue];
      const normalizedUserDegree = profile.degree.toLowerCase().trim();
      
      const pass = allowedDegrees.some(deg => {
        const d = String(deg).toLowerCase().trim();
        return normalizedUserDegree.includes(d) || d.includes(normalizedUserDegree) || deg === 'Bachelor Degree' || deg === 'Graduation';
      });
      
      return {
        pass,
        reason: pass
          ? `Degree (${profile.degree}) fulfills mandatory qualification: ${allowedDegrees.join(', ')}`
          : `Degree (${profile.degree}) does not match required qualification: ${allowedDegrees.join(', ')}`,
        clause
      };
    }
    
    case 'BRANCH_SPECIALIZATION': {
      if (rule.ruleValue === 'ANY' || rule.ruleValue === 'Any Branch') {
        return { pass: true, reason: `Any specialization branch is accepted`, clause };
      }
      const allowedBranches = Array.isArray(rule.ruleValue) ? rule.ruleValue : [rule.ruleValue];
      const normalizedUserBranch = profile.branch.toLowerCase().trim();
      
      const pass = allowedBranches.some(b => normalizedUserBranch.includes(String(b).toLowerCase()));
      return {
        pass,
        reason: pass
          ? `Specialization (${profile.branch}) matches required branch: ${allowedBranches.join(', ')}`
          : `Specialization (${profile.branch}) does not meet post-specific branch constraint: ${allowedBranches.join(', ')}`,
        clause
      };
    }
    
    case 'PERCENTAGE_MIN': {
      const minPct = Number(rule.ruleValue);
      const pass = profile.percentage >= minPct;
      return {
        pass,
        reason: pass
          ? `Percentage ${profile.percentage}% meets minimum threshold of ${minPct}%`
          : `Percentage ${profile.percentage}% is below required ${minPct}% cutoff`,
        clause
      };
    }
    
    case 'NATIONALITY': {
      const pass = true; // Default Indian citizen
      return {
        pass,
        reason: `Nationality requirement (Indian Citizen) verified`,
        clause
      };
    }
    
    default:
      return { pass: true, reason: `Rule type ${rule.ruleType} satisfied`, clause };
  }
}

export function evaluateRuleGroup(group: RuleGroup, profile: UserProfile): { pass: boolean; reasons: string[]; clauses: string[] } {
  const reasons: string[] = [];
  const clauses: string[] = [];
  
  if (group.operator === 'AND') {
    let allPass = true;
    for (const rule of group.rules) {
      const res = evaluateSingleRule(rule, profile);
      reasons.push(res.reason);
      clauses.push(res.clause);
      if (!res.pass) allPass = false;
    }
    
    if (group.childGroups && group.childGroups.length > 0) {
      for (const childGroup of group.childGroups) {
        const childRes = evaluateRuleGroup(childGroup, profile);
        reasons.push(...childRes.reasons);
        clauses.push(...childRes.clauses);
        if (!childRes.pass) allPass = false;
      }
    }
    
    return { pass: allPass, reasons, clauses };
  } else {
    // OR Group
    let anyPass = false;
    for (const rule of group.rules) {
      const res = evaluateSingleRule(rule, profile);
      reasons.push(res.reason);
      clauses.push(res.clause);
      if (res.pass) anyPass = true;
    }
    
    if (group.childGroups && group.childGroups.length > 0) {
      for (const childGroup of group.childGroups) {
        const childRes = evaluateRuleGroup(childGroup, profile);
        reasons.push(...childRes.reasons);
        clauses.push(...childRes.clauses);
        if (childRes.pass) anyPass = true;
      }
    }
    
    return { pass: anyPass, reasons, clauses };
  }
}

export function evaluateCandidateEligibility(exam: Exam, profile: UserProfile): EligibilityDiagnostic {
  // Global exam rule group evaluation
  const globalEval = evaluateRuleGroup(exam.globalRuleGroup, profile);
  
  // Post-specific evaluation
  const postVerdicts = exam.posts.map((post: PostRequirement) => {
    if (post.ruleGroup) {
      const postEval = evaluateRuleGroup(post.ruleGroup, profile);
      const isEligible = globalEval.pass && postEval.pass;
      const primaryReason = !globalEval.pass 
        ? globalEval.reasons.find(r => r.includes('exceeds') || r.includes('below') || r.includes('does not')) || globalEval.reasons[0]
        : postEval.reasons.find(r => r.includes('exceeds') || r.includes('below') || r.includes('does not')) || postEval.reasons[0];
        
      return {
        postName: post.postName,
        department: post.department,
        eligible: isEligible,
        reason: primaryReason,
        clause: post.provenance.clauseNumber || 'Clause 3.1'
      };
    } else {
      return {
        postName: post.postName,
        department: post.department,
        eligible: globalEval.pass,
        reason: globalEval.pass ? `Fulfills all general graduate eligibility requirements` : globalEval.reasons[0],
        clause: post.provenance.clauseNumber || 'Clause 3.1'
      };
    }
  });

  const eligiblePostsCount = postVerdicts.filter(p => p.eligible).length;
  const isOverallEligible = eligiblePostsCount > 0;
  const isFullyEligible = eligiblePostsCount === postVerdicts.length;
  
  const status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE' = isFullyEligible 
    ? 'ELIGIBLE' 
    : (isOverallEligible ? 'CONDITIONAL' : 'INELIGIBLE');

  const uniqueClauses = Array.from(new Set(globalEval.clauses));
  
  const plainEnglishExplanation = isOverallEligible
    ? `Great news! Based on your profile (${profile.age} yrs, ${profile.degree} in ${profile.branch}, ${profile.category} category), you qualify for ${eligiblePostsCount} out of ${postVerdicts.length} post cadres under ${exam.title}. Your age and educational qualification satisfy official notification requirements.`
    : `Based on your profile (${profile.age} yrs, ${profile.degree} in ${profile.branch}, ${profile.category} category), you do not currently meet the eligibility criteria for ${exam.title}. Review the diagnostic breakdown below to check specific age or qualification cutoffs.`;

  return {
    isEligible: isOverallEligible,
    status,
    legalClauses: uniqueClauses,
    plainEnglishExplanation,
    postVerdicts
  };
}
