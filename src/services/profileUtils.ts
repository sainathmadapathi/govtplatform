/**
 * Utility functions for UserProfile calculations
 */

export interface DetailedAge {
  years: number;
  months: number;
  days: number;
  formatted: string;
}

/**
 * Calculates candidate age in completed years based on Date of Birth and a Reference Cutoff Date.
 * @param dateOfBirth Candidate DOB in YYYY-MM-DD format
 * @param referenceDate Official cutoff date in YYYY-MM-DD format
 */
export function calculateAge(dateOfBirth: string, referenceDate: string = '2026-08-01'): number {
  const dob = new Date(dateOfBirth);
  const reference = new Date(referenceDate);

  if (Number.isNaN(dob.getTime()) || Number.isNaN(reference.getTime())) {
    return 0;
  }

  let age = reference.getFullYear() - dob.getFullYear();
  const monthDifference = reference.getMonth() - dob.getMonth();

  if (
    monthDifference < 0 ||
    (monthDifference === 0 && reference.getDate() < dob.getDate())
  ) {
    age--;
  }

  return Math.max(0, age);
}

/**
 * Calculates detailed age in years, months, and days as of crucial cutoff date.
 */
export function calculateDetailedAge(dateOfBirth: string, referenceDate: string = '2026-08-01'): DetailedAge {
  const dob = new Date(dateOfBirth);
  const ref = new Date(referenceDate);

  if (Number.isNaN(dob.getTime()) || Number.isNaN(ref.getTime())) {
    return { years: 0, months: 0, days: 0, formatted: '0 yrs' };
  }

  let years = ref.getFullYear() - dob.getFullYear();
  let months = ref.getMonth() - dob.getMonth();
  let days = ref.getDate() - dob.getDate();

  if (days < 0) {
    months -= 1;
    // Get days in previous month
    const prevMonthLastDay = new Date(ref.getFullYear(), ref.getMonth(), 0).getDate();
    days += prevMonthLastDay;
  }

  if (months < 0) {
    years -= 1;
    months += 12;
  }

  return {
    years: Math.max(0, years),
    months: Math.max(0, months),
    days: Math.max(0, days),
    formatted: `${years} yrs, ${months} mos, ${days} days`
  };
}

/**
 * Returns Category Age Relaxation in years as per official SSC CGL rules.
 */
export function getCategoryAgeRelaxation(category: string): number {
  switch (category) {
    case 'OBC':
      return 3;
    case 'SC':
    case 'ST':
      return 5;
    case 'PwBD':
      return 10;
    default:
      return 0;
  }
}
