"""Shared gradebook builders for parent portal, teachers, and school managers."""

from apps.grades.models import Assessment, AssessmentType

TYPE_ORDER = {
    AssessmentType.QUIZ: 0,
    AssessmentType.HOMEWORK: 1,
    AssessmentType.MIDTERM: 2,
    AssessmentType.FINAL: 3,
    AssessmentType.OTHER: 4,
}


def build_student_gradebook(student):
    """
    Matrix gradebook:
    - rows = subjects
    - columns = assessment slots aligned across subjects
    """
    if student.classroom_id:
        assessments = (
            Assessment.objects.filter(school=student.school, classroom_id=student.classroom_id)
            .select_related('subject', 'term')
            .order_by('term__academic_year', 'term__name', 'subject__name', 'date', 'name')
        )
    else:
        assessments = (
            Assessment.objects.filter(id__in=student.grades.values_list('assessment_id', flat=True))
            .select_related('subject', 'term')
            .order_by('term__academic_year', 'term__name', 'subject__name', 'date', 'name')
        )

    grade_by_assessment = {
        g.assessment_id: g for g in student.grades.select_related('assessment')
    }

    terms: dict = {}
    for assessment in assessments:
        term = assessment.term
        term_entry = terms.setdefault(
            term.id,
            {
                'term_id': term.id,
                'term_name': term.name,
                'academic_year': term.academic_year,
                'is_current': term.is_current,
                'by_subject': {},
            },
        )
        subject = assessment.subject
        subject_entry = term_entry['by_subject'].setdefault(
            subject.id,
            {
                'subject_id': subject.id,
                'subject_name': subject.name,
                'items': [],
            },
        )
        grade = grade_by_assessment.get(assessment.id)
        try:
            type_label = AssessmentType(assessment.assessment_type).label
        except ValueError:
            type_label = assessment.assessment_type
        subject_entry['items'].append(
            {
                'assessment_id': assessment.id,
                'assessment_type': assessment.assessment_type,
                'assessment_type_label': type_label,
                'name': assessment.name,
                'date': assessment.date,
                'score': grade.score if grade else None,
                'max_score': assessment.max_score,
            }
        )

    gradebook_terms = []
    for term_entry in sorted(
        terms.values(),
        key=lambda t: (not t.get('is_current', False), t['academic_year'], t['term_name']),
    ):
        type_counts: dict[str, int] = {}
        for subject_entry in term_entry['by_subject'].values():
            counts: dict[str, int] = {}
            for item in subject_entry['items']:
                t = item['assessment_type']
                counts[t] = counts.get(t, 0) + 1
            for t, n in counts.items():
                type_counts[t] = max(type_counts.get(t, 0), n)

        columns = []
        for assessment_type, _order in sorted(TYPE_ORDER.items(), key=lambda x: x[1]):
            count = type_counts.get(assessment_type, 0)
            try:
                type_label = AssessmentType(assessment_type).label
            except ValueError:
                type_label = assessment_type
            for idx in range(1, count + 1):
                label = type_label if count == 1 else f'{type_label} {idx}'
                columns.append(
                    {
                        'key': f'{assessment_type}_{idx}',
                        'label': label,
                        'assessment_type': assessment_type,
                        'assessment_type_label': type_label,
                        'index': idx,
                    }
                )

        rows = []
        for subject_entry in sorted(
            term_entry['by_subject'].values(),
            key=lambda s: s['subject_name'],
        ):
            by_type: dict[str, list] = {}
            for item in sorted(
                subject_entry['items'],
                key=lambda i: (
                    TYPE_ORDER.get(i['assessment_type'], 99),
                    i['date'] or '',
                    i['name'],
                ),
            ):
                by_type.setdefault(item['assessment_type'], []).append(item)

            cells = {}
            scores = []
            for col in columns:
                items = by_type.get(col['assessment_type'], [])
                item = items[col['index'] - 1] if col['index'] - 1 < len(items) else None
                if item is None:
                    cells[col['key']] = None
                    continue
                cell = {
                    'assessment_id': item['assessment_id'],
                    'name': item['name'],
                    'score': item['score'],
                    'max_score': item['max_score'],
                }
                cells[col['key']] = cell
                if item['score'] is not None:
                    scores.append(float(item['score']))

            rows.append(
                {
                    'subject_id': subject_entry['subject_id'],
                    'subject_name': subject_entry['subject_name'],
                    'cells': cells,
                    'average': round(sum(scores) / len(scores), 2) if scores else None,
                }
            )

        gradebook_terms.append(
            {
                'term_id': term_entry['term_id'],
                'term_name': term_entry['term_name'],
                'academic_year': term_entry['academic_year'],
                'is_current': term_entry['is_current'],
                'columns': columns,
                'rows': rows,
            }
        )

    return {'terms': gradebook_terms}
