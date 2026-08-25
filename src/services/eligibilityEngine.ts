import { Exam, UserProfile, EligibilityDiagnostic, PostVerdict, PostRequirement } from '../types/exam';
import { calculateAge, calculateDetailedAge, getCategoryAgeRelaxation } from './profileUtils';

export function normalizeDegree(value: string): string {
  const normalized = (value || '').toLowerCase().trim();
  if (normalized.includes('b.tech') || normalized.includes('b.e') || normalized.includes('engineering')) {
    return 'bachelor';
  }
  if (
    normalized.includes('b.sc') ||
    normalized.includes('b.a') ||
    normalized.includes('b.com') ||
    normalized.includes('bba') ||
    normalized.includes('bca') ||
    normalized.includes('bachelor') ||
    normalized.includes('graduation') ||
    normalized.includes('degree')
  ) {
    return 'bachelor';
  }
  return normalized;
}

export function evaluatePostEligibility(
  post: PostRequirement,
  profile: UserProfile,
  crucialDate: string = '2026-08-01'
): PostVerdict {
  const age = calculateAge(profile.dateOfBirth, crucialDate);
  const relaxation = getCategoryAgeRelaxation(profile.category);
  const maxPermissibleAge = post.maxAge + relaxation;
  const userDegreeNorm = normalizeDegree(profile.degree);
  const isBachelor = userDegreeNorm.includes('bachelor') || userDegreeNorm.includes('degree');

  let ageStatus: 'OK' | 'EXCEEDED' | 'UNDERAGE' = 'OK';
  let qualStatus: 'OK' | 'DISQUALIFIED' = 'OK';
  let physicalStatus: 'OK' | 'RESTRICTED' = 'OK';
  const reasons: string[] = [];

  // 1. Age Verification
  if (age < post.minAge) {
    ageStatus = 'UNDERAGE';
    reasons.push(`Underage: ${age} yrs is below minimum requirement of ${post.minAge} yrs`);
  } else if (age > maxPermissibleAge) {
    ageStatus = 'EXCEEDED';
    reasons.push(
      `Age Exceeded: ${age} yrs exceeds permissible limit of ${maxPermissibleAge} yrs (${post.maxAge} base + ${relaxation} yrs ${profile.category} relaxation)`
    );
  } else {
    reasons.push(
      `Age Verified: ${age} yrs (as of ${crucialDate}) is within ${post.minAge}-${maxPermissibleAge} yrs limit`
    );
  }

  // 2. Educational Qualification Verification
  if (!isBachelor && !profile.degree.toLowerCase().includes('final year')) {
    qualStatus = 'DISQUALIFIED';
    reasons.push(`Qualification: Requires Bachelor's Degree from recognized university`);
  } else {
    // Check post-specific specialized qualifications
    if (post.id === 'post-jso') {
      const hasMaths = profile.mathsIn12thWith60Percent === true;
      const hasStats = profile.statisticsInDegree === true || (profile.branch || '').toLowerCase().includes('stat');
      if (!hasMaths && !hasStats) {
        qualStatus = 'DISQUALIFIED';
        reasons.push(`JSO Special Criteria: Requires 60% in Maths in 12th OR Statistics as a subject in Degree`);
      } else {
        reasons.push(`JSO Criteria Satisfied: ${hasMaths ? '60%+ in 12th Maths' : 'Statistics in Degree'} verified`);
      }
    } else if (post.id === 'post-stat-inv') {
      const hasStatsDegree = profile.statisticsInDegree === true || (profile.branch || '').toLowerCase().includes('stat');
      if (!hasStatsDegree) {
        qualStatus = 'DISQUALIFIED';
        reasons.push(`Statistical Investigator Gr II: Requires Statistics as a subject in all 3 years of Degree`);
      } else {
        reasons.push(`Statistical Criteria Satisfied: Statistics in all semesters verified`);
      }
    } else {
      reasons.push(`Essential Qualification: Bachelor's Degree verified`);
    }
  }

  // 3. Physical Standards Check
  if (post.physicalRequired) {
    if (profile.physicalFitnessDeclared === false) {
      physicalStatus = 'RESTRICTED';
      reasons.push(`Physical Criteria: Requires mandatory physical fitness standards (${post.physicalNote || 'Physical test & measurement'})`);
    }
    if (post.colorBlindnessAllowed === false && profile.colorBlind === true) {
      physicalStatus = 'RESTRICTED';
      reasons.push(`Medical Criteria: Color blindness is NOT permitted for this enforcement post`);
    }
  }

  const eligible = ageStatus === 'OK' && qualStatus === 'OK' && physicalStatus === 'OK';

  return {
    postId: post.id,
    postName: post.postName,
    department: post.department,
    payLevel: post.payLevel,
    eligible,
    ageStatus,
    calculatedAge: age,
    maxPermissibleAge,
    qualStatus,
    physicalStatus,
    reason: reasons.join(' • '),
    officialClause: post.provenance.clauseNumber || 'Section 3.1 & Annexure-VII'
  };
}

export function evaluateEligibility(exam: Exam, profile: UserProfile): EligibilityDiagnostic {
  const crucialDate = exam.crucialEligibilityDate || '2026-08-01';
  const detailedAge = calculateDetailedAge(profile.dateOfBirth, crucialDate);
  const relaxation = getCategoryAgeRelaxation(profile.category);
  const userAge = detailedAge.years;

  const legalClauses: string[] = [
    'SSC CGL Notification Section 3.1: Crucial date for age limit calculation is 01-08-2026',
    `Section 3.2: Permissible upper age relaxation for ${profile.category} candidates is +${relaxation} years`,
    'Section 8.1: Essential Educational Qualification: Bachelor’s Degree from a recognized University or equivalent (as on 01-08-2026)'
  ];

  const postVerdicts: PostVerdict[] = exam.posts.map(post =>
    evaluatePostEligibility(post, profile, crucialDate)
  );

  const eligibleCount = postVerdicts.filter(p => p.eligible).length;
  const totalCount = postVerdicts.length;

  let status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE' = 'INELIGIBLE';
  let plainEnglishExplanation = '';

  if (eligibleCount === totalCount) {
    status = 'ELIGIBLE';
    plainEnglishExplanation = `Congratulations! Based on official SSC CGL 2026 rules, you are fully eligible for ALL ${totalCount} posts (including Group B Gazetted & Non-Gazetted posts) with your calculated age of ${detailedAge.formatted} as on ${crucialDate}.`;
  } else if (eligibleCount > 0) {
    status = 'CONDITIONAL';
    plainEnglishExplanation = `You are eligible for ${eligibleCount} out of ${totalCount} posts. Some posts (like JSO, Statistical Investigator, or 18-27 age bracket posts) have specific age brackets or subject requirements that you do not satisfy.`;
  } else {
    status = 'INELIGIBLE';
    if (userAge < 18) {
      plainEnglishExplanation = `You are currently ${userAge} years old as of the crucial cutoff date (${crucialDate}). Minimum age required for SSC CGL is 18 years.`;
    } else {
      plainEnglishExplanation = `Your calculated age (${userAge} years as of ${crucialDate}) exceeds the upper age limit for all SSC CGL posts even after applying ${profile.category} category relaxation (+${relaxation} years).`;
    }
  }

  return {
    isEligible: eligibleCount > 0,
    status,
    calculatedAgeOnCutoff: {
      years: detailedAge.years,
      months: detailedAge.months,
      days: detailedAge.days,
      crucialDate
    },
    categoryRelaxationApplied: `${profile.category} (+${relaxation} Years Relaxation Applied)`,
    totalEligiblePosts: eligibleCount,
    totalAvailablePosts: totalCount,
    legalClauses,
    plainEnglishExplanation,
    postVerdicts
  };
}

export const evaluateCandidateEligibility = evaluateEligibility;
