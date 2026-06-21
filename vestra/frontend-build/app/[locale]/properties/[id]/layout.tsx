import type { Metadata } from 'next'

async function getProperty(id: string) {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const res = await fetch(`${apiUrl}/api/properties/${id}`, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(3000),
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>
}): Promise<Metadata> {
  const { id } = await params
  const property = await getProperty(id)

  if (property) {
    const title = `${property.title} — Vestra`
    const description =
      `${property.title} in ${property.city || 'Kenya'}. ${property.bedrooms ? `${property.bedrooms} bed, ` : ''}${property.bathrooms ? `${property.bathrooms} bath` : ''}${property.price ? `. Price: KES ${Number(property.price).toLocaleString()}` : ''}`

    return {
      title,
      description,
      openGraph: {
        title,
        description: `View this property in ${property.city || 'Kenya'} on Vestra.`,
        images: property.images?.length
          ? [{ url: property.images[0], width: 1200, height: 630 }]
          : [],
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
        images: property.images?.length ? [property.images[0]] : [],
      },
    }
  }

  return {
    title: 'Property Details — Vestra',
    description: 'View property details, trust scores, and verification history on Vestra.',
  }
}

export default function PropertyLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
