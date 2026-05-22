import React from 'react'
import { Document, Page, Text, View, StyleSheet, Font } from '@react-pdf/renderer'
import type { ResumeData, TemplateId } from '@/lib/resume-types'

// Register fonts
Font.register({
  family: 'Inter',
  fonts: [
    { src: 'https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hjp-Ek-_EeA.woff2', fontWeight: 400 },
    { src: 'https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6fAZ9hjp-Ek-_EeA.woff2', fontWeight: 600 },
    { src: 'https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuFuYAZ9hjp-Ek-_EeA.woff2', fontWeight: 700 },
  ],
})

const formatDate = (date: string) => {
  if (!date) return ''
  const [year, month] = date.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${months[parseInt(month) - 1]} ${year}`
}

const templateColors = {
  minimal: { primary: '#171717', accent: '#525252' },
  modern: { primary: '#2563eb', accent: '#3b82f6' },
  classic: { primary: '#b45309', accent: '#d97706' },
  developer: { primary: '#059669', accent: '#10b981' },
}

const createStyles = (template: TemplateId) => {
  const colors = templateColors[template]
  
  return StyleSheet.create({
    page: {
      padding: 40,
      fontFamily: 'Inter',
      fontSize: 10,
      color: '#171717',
      backgroundColor: '#ffffff',
    },
    header: {
      marginBottom: 20,
      textAlign: template === 'developer' ? 'left' : 'center',
      borderLeftWidth: template === 'developer' ? 3 : 0,
      borderLeftColor: colors.primary,
      paddingLeft: template === 'developer' ? 12 : 0,
    },
    name: {
      fontSize: 24,
      fontWeight: 700,
      color: template === 'modern' ? colors.primary : '#171717',
      marginBottom: 4,
    },
    title: {
      fontSize: 11,
      color: template === 'developer' ? colors.primary : '#525252',
      fontStyle: template === 'classic' ? 'italic' : 'normal',
    },
    contactRow: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      justifyContent: template === 'developer' ? 'flex-start' : 'center',
      gap: 12,
      marginTop: 8,
      fontSize: 9,
      color: '#525252',
    },
    contactItem: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    section: {
      marginBottom: 16,
    },
    sectionTitle: {
      fontSize: 10,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: 1,
      color: template === 'minimal' ? '#525252' : colors.primary,
      marginBottom: 8,
      borderBottomWidth: template === 'minimal' || template === 'classic' ? 1 : 0,
      borderBottomColor: template === 'classic' ? colors.accent : '#e5e5e5',
      paddingBottom: 4,
    },
    summaryText: {
      color: '#525252',
      lineHeight: 1.5,
    },
    experienceItem: {
      marginBottom: 12,
    },
    experienceHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
    },
    experiencePosition: {
      fontWeight: 600,
      fontSize: 11,
    },
    experienceCompany: {
      color: colors.primary,
      fontSize: 10,
    },
    experienceDate: {
      fontSize: 9,
      color: '#525252',
    },
    experienceLocation: {
      fontSize: 9,
      color: '#737373',
    },
    bulletList: {
      marginTop: 6,
    },
    bulletItem: {
      flexDirection: 'row',
      marginBottom: 3,
    },
    bullet: {
      width: 12,
      color: colors.accent,
    },
    bulletText: {
      flex: 1,
      color: '#525252',
    },
    skillsContainer: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 6,
    },
    skillTag: {
      backgroundColor: template === 'minimal' ? '#f5f5f5' : `${colors.primary}10`,
      color: template === 'minimal' ? '#525252' : colors.primary,
      paddingHorizontal: 8,
      paddingVertical: 3,
      borderRadius: 4,
      fontSize: 9,
    },
    projectItem: {
      marginBottom: 10,
    },
    projectName: {
      fontWeight: 600,
      fontSize: 10,
    },
    projectDescription: {
      color: '#525252',
      marginTop: 2,
    },
    projectTech: {
      fontSize: 9,
      color: '#737373',
      marginTop: 3,
    },
    educationItem: {
      marginBottom: 8,
    },
    educationInstitution: {
      fontWeight: 600,
      fontSize: 10,
    },
    educationDegree: {
      color: '#525252',
      fontSize: 10,
    },
  })
}

interface ResumeDocumentProps {
  data: ResumeData
  template: TemplateId
}

export function ResumeDocument({ data, template }: ResumeDocumentProps) {
  const styles = createStyles(template)

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.name}>{data.name}</Text>
          <Text style={styles.title}>{data.title}</Text>
          <View style={styles.contactRow}>
            {data.email && <Text style={styles.contactItem}>{data.email}</Text>}
            {data.phone && <Text style={styles.contactItem}>{data.phone}</Text>}
            {data.location && <Text style={styles.contactItem}>{data.location}</Text>}
            {data.website && <Text style={styles.contactItem}>{data.website}</Text>}
            {data.linkedin && <Text style={styles.contactItem}>{data.linkedin}</Text>}
            {data.github && <Text style={styles.contactItem}>{data.github}</Text>}
          </View>
        </View>

        {/* Summary */}
        {data.summary && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Summary</Text>
            <Text style={styles.summaryText}>{data.summary}</Text>
          </View>
        )}

        {/* Experience */}
        {data.experience.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Experience</Text>
            {data.experience.map((exp) => (
              <View key={exp.id} style={styles.experienceItem}>
                <View style={styles.experienceHeader}>
                  <View>
                    <Text style={styles.experiencePosition}>{exp.position}</Text>
                    <Text style={styles.experienceCompany}>{exp.company}</Text>
                    {exp.location && <Text style={styles.experienceLocation}>{exp.location}</Text>}
                  </View>
                  <Text style={styles.experienceDate}>
                    {formatDate(exp.startDate)} - {exp.current ? 'Present' : formatDate(exp.endDate)}
                  </Text>
                </View>
                <View style={styles.bulletList}>
                  {exp.description.map((item, i) => (
                    <View key={i} style={styles.bulletItem}>
                      <Text style={styles.bullet}>•</Text>
                      <Text style={styles.bulletText}>{item}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Skills */}
        {data.skills.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Skills</Text>
            <View style={styles.skillsContainer}>
              {data.skills.map((skill, i) => (
                <Text key={i} style={styles.skillTag}>{skill}</Text>
              ))}
            </View>
          </View>
        )}

        {/* Projects */}
        {data.projects.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Projects</Text>
            {data.projects.map((project) => (
              <View key={project.id} style={styles.projectItem}>
                <Text style={styles.projectName}>{project.name}</Text>
                <Text style={styles.projectDescription}>{project.description}</Text>
                <Text style={styles.projectTech}>
                  {project.technologies.join(' • ')}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Education */}
        {data.education.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Education</Text>
            {data.education.map((edu) => (
              <View key={edu.id} style={styles.educationItem}>
                <View style={styles.experienceHeader}>
                  <View>
                    <Text style={styles.educationInstitution}>{edu.institution}</Text>
                    <Text style={styles.educationDegree}>
                      {edu.degree} in {edu.field}
                      {edu.gpa && ` • GPA: ${edu.gpa}`}
                    </Text>
                  </View>
                  <Text style={styles.experienceDate}>
                    {formatDate(edu.startDate)} - {formatDate(edu.endDate)}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}
      </Page>
    </Document>
  )
}
