function SectionCard({ title, action, children, ariaLabel }) {
  return (
    <section
      aria-label={ariaLabel || title}
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export default SectionCard
