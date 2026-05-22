import { NextRequest, NextResponse } from 'next/server'
import ReactPDF from '@react-pdf/renderer'
import { ResumeDocument } from './resume-document'
import type { ResumeData, TemplateId } from '@/lib/resume-types'

export async function POST(request: NextRequest) {
  try {
    const { data, template } = await request.json() as { data: ResumeData; template: TemplateId }

    if (!data || !data.name) {
      return NextResponse.json(
        { error: 'Resume data is required' },
        { status: 400 }
      )
    }

    const pdfStream = await ReactPDF.renderToStream(
      <ResumeDocument data={data} template={template} />
    )

    // Convert stream to buffer
    const chunks: Uint8Array[] = []
    for await (const chunk of pdfStream) {
      chunks.push(chunk)
    }
    const buffer = Buffer.concat(chunks)

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${data.name.replace(/\s+/g, '_')}_Resume.pdf"`,
      },
    })
  } catch (error) {
    console.error('PDF export error:', error)
    return NextResponse.json(
      { error: 'Failed to generate PDF' },
      { status: 500 }
    )
  }
}
