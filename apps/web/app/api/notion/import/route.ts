import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { pageId } = await request.json()

    if (!pageId) {
      return NextResponse.json(
        { error: 'Page ID is required' },
        { status: 400 }
      )
    }

    const response = await fetch(
      `${process.env.API_URL}/api/v1/notion/import`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ page_id: pageId }),
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to import notion page" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data);

    // This is a placeholder that demonstrates the expected data structure
    // In production, you would use the Notion API to fetch the actual page content
    // The MCP Notion integration can be used to query and retrieve page data

    // For now, return a message indicating the integration point
    return NextResponse.json({
      message: 'Notion integration ready',
      pageId,
      resume: {
        name: 'Imported User',
        title: 'Software Developer',
        email: 'user@example.com',
        phone: '',
        location: '',
        website: '',
        linkedin: '',
        github: '',
        summary: 'Resume imported from Notion. Configure your Notion page with the appropriate structure.',
        experience: [],
        education: [],
        skills: [],
        projects: [],
      }
    })
  } catch (error) {
    console.error('Notion import error:', error)
    return NextResponse.json(
      { error: 'Failed to import from Notion' },
      { status: 500 }
    )
  }
}
