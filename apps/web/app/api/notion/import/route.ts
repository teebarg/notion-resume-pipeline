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
  } catch (error) {
    console.error('Notion import error:', error)
    return NextResponse.json(
      { error: 'Failed to import from Notion' },
      { status: 500 }
    )
  }
}
