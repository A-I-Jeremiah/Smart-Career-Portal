export const DEPARTMENT_SUBJECTS = {
  Science: [
    'English',
    'Mathematics',
    'Civic Education',
    'Physics',
    'Chemistry',
    'Biology',
    'Further Mathematics',
    'Agricultural Science',
    'Computer Science',
    'Geography',
  ],
  Arts: [
    'English',
    'Mathematics',
    'Literature in English',
    'Government',
    'CRS/IRK',
    'History',
    'Economics',
    'Yoruba/Hausa/Igbo',
    'Civic Education',
  ],
  Commercial: [
    'English',
    'Mathematics',
    'Civic Education',
    'Economics',
    'Accounting',
    'Commerce',
    'Business Studies',
    'Government',
    'Office Practice',
    'Insurance',
  ],
};

export const SUBJECT_TO_API_KEY = {
  'mathematics': 'mathematics',
  'english': 'english',
  'english language': 'english',
  'civic education': 'civic_education',
  'physics': 'physics',
  'chemistry': 'chemistry',
  'biology': 'biology',
  'further mathematics': 'further_mathematics',
  'agricultural science': 'agricultural_science',
  'agriculture': 'agricultural_science',
  'geography': 'geography',
  'technical drawing': 'technical_drawing',
  'computer studies': 'computer_studies',
  'computer science': 'computer_studies',
  'yoruba/hausa/igbo': 'igbo_hausa',
  'yoruba': 'yoruba',
  'hausa': 'igbo_hausa',
  'igbo': 'igbo_hausa',
  'data processing': 'data_processing',
  'literature in english': 'literature_in_english',
  'crs/irk': 'christian_religious_studies_islamic_studies',
  'crs': 'christian_religious_studies_islamic_studies',
  'irk': 'christian_religious_studies_islamic_studies',
  'creative arts': 'creative_arts',
  'cultural and creative arts': 'creative_arts',
  'history': 'government',
  'economics': 'economics',
  'accounting': 'financial_accounting',
  'financial accounting': 'financial_accounting',
  'commerce': 'commerce',
  'business studies': 'commerce',
  'office practice': 'commerce',
  'insurance': 'commerce',
  'government': 'government',
  'marketing': 'marketing',
};

export const scoreToGrade = (score) => {
  const s = parseFloat(score || 0);
  if (s >= 75) return 'A';
  if (s >= 65) return 'B';
  if (s >= 50) return 'C';
  if (s >= 45) return 'D';
  if (s >= 40) return 'E';
  return 'F';
};

const subjectCategoryGroups = {
  Science: [
    'mathematics', 'physics', 'chemistry', 'biology', 'further_mathematics',
    'computer_studies', 'geography', 'technical_drawing', 'agricultural_science', 'data_processing',
  ],
  Arts: [
    'literature_in_english', 'yoruba', 'igbo_hausa', 'christian_religious_studies_islamic_studies',
    'creative_arts', 'government', 'economics', 'history', 'english',
  ],
  Commercial: [
    'economics', 'financial_accounting', 'commerce', 'marketing',
    'government', 'data_processing', 'business studies', 'office practice', 'insurance',
  ],
};

export const getSubjectsForDepartment = (dept) => {
  return DEPARTMENT_SUBJECTS[dept] || ['English', 'Mathematics'];
};

const numericScore = (value) => {
  const score = Number(value || 0);
  return Number.isFinite(score) ? parseFloat(score.toFixed(2)) : 0;
};

const letterGradePoint = (grade) => {
  switch ((grade || '').toUpperCase()) {
    case 'A':
      return 8;
    case 'B':
      return 6;
    case 'C':
      return 5;
    case 'D':
      return 3;
    case 'E':
      return 2;
    case 'F':
      return 1;
    default:
      return 5;
  }
};

export const buildPredictPayload = (results, department, testScores) => {
  const payload = {
    gender: 'Unknown',
    age: 17,
    school_type: 'Unknown',
    department: department || 'Science',
    academic_strength: 'Unknown',
    best_subject_category: 'Unknown',
    confidence_level: 'Unknown',
    career_influence: 'Unknown',
    aptitude_score_10: numericScore(testScores.aptitude),
    cognitive_score_10: numericScore(testScores.cognitive),
    psychometric_avg_5: numericScore(testScores.psychometric),
    sentiment_avg_5: numericScore(testScores.sentiment),
    waec_credits: 5,
    cgpa: 0.0,
    course_alignment: 0,
    waec_year: new Date().getFullYear(),
  };

  const categoryTotals = {
    Science: { score: 0, count: 0 },
    Arts: { score: 0, count: 0 },
    Commercial: { score: 0, count: 0 },
  };
  let totalScore = 0;
  let totalGradePoints = 0;
  let gradeCount = 0;

  const uniqueKeys = new Set(Object.values(SUBJECT_TO_API_KEY));
  uniqueKeys.forEach((key) => {
    payload[key] = 'UNKNOWN';
  });

  results.forEach((row) => {
    const subject = String(row.subject).trim().toLowerCase();
    const apiKey = SUBJECT_TO_API_KEY[subject];
    const score = Number(row.score);
    if (!apiKey || Number.isNaN(score)) {
      return;
    }

    const grade = scoreToGrade(score);
    payload[apiKey] = grade;
    totalScore += score;
    totalGradePoints += letterGradePoint(grade);
    gradeCount += 1;

    Object.entries(subjectCategoryGroups).forEach(([group, keys]) => {
      if (keys.includes(apiKey)) {
        categoryTotals[group].score += score;
        categoryTotals[group].count += 1;
      }
    });
  });

  const averageScore = gradeCount ? totalScore / gradeCount : 0;
  const averageGradePoint = gradeCount ? totalGradePoints / gradeCount : 5;
  payload.waec_credits = Math.min(9, Math.max(1, gradeCount));
  payload.cgpa = parseFloat((averageGradePoint / 2).toFixed(2));
  payload.course_alignment = Math.round(averageScore / 20);

  const categoryRanks = Object.entries(categoryTotals)
    .map(([category, data]) => ({
      category,
      average: data.count ? data.score / data.count : 0,
    }))
    .sort((a, b) => b.average - a.average);

  payload.best_subject_category = categoryRanks[0]?.average > 0
    ? categoryRanks[0].category
    : department || 'Science';

  if (averageScore >= 75) {
    payload.academic_strength = 'Very Strong';
  } else if (averageScore >= 60) {
    payload.academic_strength = 'Strong';
  } else if (averageScore >= 50) {
    payload.academic_strength = 'Average';
  } else {
    payload.academic_strength = 'Developing';
  }

  const averageTestScore = (payload.aptitude_score_10 + payload.cognitive_score_10) / 2;
  if (averageTestScore >= 8 || payload.sentiment_avg_5 >= 4) {
    payload.confidence_level = 'High';
  } else if (averageTestScore >= 6 || payload.sentiment_avg_5 >= 3.5) {
    payload.confidence_level = 'Moderate';
  } else {
    payload.confidence_level = 'Low';
  }

  payload.career_influence = payload.sentiment_avg_5 >= 4
    ? 'Positive'
    : payload.sentiment_avg_5 >= 3
      ? 'Neutral'
      : 'Needs Support';

  return payload;
};
