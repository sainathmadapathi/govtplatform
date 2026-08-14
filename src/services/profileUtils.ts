/**
 * Utility functions for UserProfile calculations
 */

/**
 * Calculates candidate age in completed years based on Date of Birth and a Reference Cutoff Date.
 * @param dateOfBirth Candidate DOB in YYYY-MM-DD format
 * @param referenceDate Official cutoff date in YYYY-MM-DD format
 */
export function calculateAge(dateOfBirth: string, referenceDate: string): number {
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

  return age;
}
