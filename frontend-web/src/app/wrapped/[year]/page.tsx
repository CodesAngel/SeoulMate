import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { WrappedStory } from "@/components/wrapped-story";
import { NO_INDEX } from "@/lib/site";
import { WRAPPED_FIRST_YEAR } from "@/lib/wrapped";

type Props = { params: Promise<{ year: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { year } = await params;
  return { title: `Your ${year} Wrapped`, ...NO_INDEX };
}

export default async function WrappedYearPage({ params }: Props) {
  const year = Number((await params).year);
  // Future years are checked by the API (it knows today's date at request time).
  if (!Number.isInteger(year) || year < WRAPPED_FIRST_YEAR || year > 2100) notFound();
  return <WrappedStory year={year} />;
}
