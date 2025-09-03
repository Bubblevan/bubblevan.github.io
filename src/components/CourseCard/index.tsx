import React from 'react'
import Link from '@docusaurus/Link'
import styles from './styles.module.css'

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
  return (
    <Link to={course.path} className={styles.courseLink}>
      <div className={`${styles.courseCard} ${className || ''}`}>
        <div className={styles.semester}>{course.semester}</div>
        <h3 className={styles.title}>{course.title}</h3>
        {course.description && (
          <p className={styles.description}>{course.description}</p>
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
  return (
    <div className={`${styles.courseGrid} ${className || ''}`}>
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