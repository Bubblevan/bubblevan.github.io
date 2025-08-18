import React from 'react'
import Link from '@docusaurus/Link'

interface Course {
  title: string
  path: string
  semester: string
  description?: string
}

interface CourseCardProps {
  course: Course
  className?: string
}

const CourseCard: React.FC<CourseCardProps> = ({ course, className }) => {

  const cardStyle = {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '16px',
    cursor: 'pointer',
    backgroundColor: '#ffffff',
    marginBottom: '16px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    transition: 'all 0.2s ease'
  }

  const semesterStyle = {
    fontSize: '14px',
    color: '#2563eb',
    fontWeight: '500',
    marginBottom: '8px'
  }

  const titleStyle = {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: '8px'
  }

  const descriptionStyle = {
    fontSize: '14px',
    color: '#6b7280',
    lineHeight: '1.5'
  }

  return (
    <Link to={course.path} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div style={cardStyle}>
        <div style={semesterStyle}>{course.semester}</div>
        <h3 style={titleStyle}>{course.title}</h3>
        {course.description && (
          <p style={descriptionStyle}>{course.description}</p>
        )}
      </div>
    </Link>
  )
}

interface CourseGridProps {
  courses: Course[]
  className?: string
}

const CourseGrid: React.FC<CourseGridProps> = ({ courses, className }) => {
  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '16px',
    width: '100%'
  }

  return (
    <div style={gridStyle}>
      {courses.map((course, index) => (
        <CourseCard key={index} course={course} />
      ))}
    </div>
  )
}

export { CourseCard, CourseGrid }
export type { Course }

// 添加默认导出
export default CourseGrid