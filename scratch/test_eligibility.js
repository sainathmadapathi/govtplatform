import { evaluateCandidateEligibility } from '../src/services/eligibilityEngine.ts';
import { SSC_CGL_EXAM } from '../src/data/examsData.ts';

console.log("=== GOVOS ELIGIBILITY MATRIX TEST RUNNER ===");

// Test 1: Eligible candidate (Age 21, B.Tech CSE, General, Indian)
const profile1 = {
  dateOfBirth: '2005-05-15',
  degree: 'B.Tech',
  branch: 'Computer Science & Engineering',
  percentage: 72,
  category: 'GENERAL',
  gender: 'Male',
  domicileState: 'Telangana',
  nationality: 'INDIAN'
};
const res1 = evaluateCandidateEligibility(SSC_CGL_EXAM, profile1);
console.log("\n[TEST 1] Eligible Candidate:");
console.log("Status:", res1.status);
console.log("Is Overall Eligible:", res1.isEligible);
console.log("Explanation:", res1.plainEnglishExplanation);
console.log("Post Verdicts Count:", res1.postVerdicts.length);
res1.postVerdicts.forEach(pv => console.log(`  - ${pv.postName}: ${pv.eligible ? '✅' : '❌'} (${pv.reason})`));

// Test 2: Too Old candidate (Born 1990, age 36)
const profile2 = {
  dateOfBirth: '1990-01-01',
  degree: 'B.Tech',
  branch: 'Computer Science',
  percentage: 72,
  category: 'GENERAL',
  gender: 'Male',
  domicileState: 'Telangana',
  nationality: 'INDIAN'
};
const res2 = evaluateCandidateEligibility(SSC_CGL_EXAM, profile2);
console.log("\n[TEST 2] Too Old Candidate:");
console.log("Status:", res2.status);
console.log("Is Overall Eligible:", res2.isEligible);
res2.postVerdicts.forEach(pv => console.log(`  - ${pv.postName}: ${pv.eligible ? '✅' : '❌'} (${pv.reason})`));

// Test 3: Wrong Nationality (OTHER)
const profile3 = {
  dateOfBirth: '2005-05-15',
  degree: 'B.Tech',
  branch: 'Computer Science',
  percentage: 72,
  category: 'GENERAL',
  gender: 'Male',
  domicileState: 'Telangana',
  nationality: 'OTHER'
};
const res3 = evaluateCandidateEligibility(SSC_CGL_EXAM, profile3);
console.log("\n[TEST 3] Non-Indian Citizen:");
console.log("Status:", res3.status);
console.log("Is Overall Eligible:", res3.isEligible);

// Test 4: Wrong Degree (Class 10th)
const profile4 = {
  dateOfBirth: '2005-05-15',
  degree: 'Class 10th',
  branch: 'General',
  percentage: 72,
  category: 'GENERAL',
  gender: 'Male',
  domicileState: 'Telangana',
  nationality: 'INDIAN'
};
const res4 = evaluateCandidateEligibility(SSC_CGL_EXAM, profile4);
console.log("\n[TEST 4] Class 10th Candidate:");
console.log("Status:", res4.status);
console.log("Is Overall Eligible:", res4.isEligible);

// Test 5: SC Category Relaxation (Born 1996, age 30, SC Category gets +5 yrs max 32)
const profile5 = {
  dateOfBirth: '1996-05-15',
  degree: 'B.Tech',
  branch: 'Computer Science',
  percentage: 72,
  category: 'SC',
  gender: 'Male',
  domicileState: 'Telangana',
  nationality: 'INDIAN'
};
const res5 = evaluateCandidateEligibility(SSC_CGL_EXAM, profile5);
console.log("\n[TEST 5] SC Category Age Relaxation Candidate:");
console.log("Status:", res5.status);
console.log("Is Overall Eligible:", res5.isEligible);
res5.postVerdicts.forEach(pv => console.log(`  - ${pv.postName}: ${pv.eligible ? '✅' : '❌'} (${pv.reason})`));
