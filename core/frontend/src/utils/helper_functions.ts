/* Asynchronously wait for a given interval. */
/**
 * @param interval - Time in milliseconds to wait after the previous request is done
* */
export function sleep(interval: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, interval))
}

/* Call a given function periodically for a given interval. */
/**
 * @param func - Function to be called.
 * @param interval - Time in milliseconds to wait after the previous request is done
* */
export async function callPeriodically(func: () => Promise<void>, interval: number): Promise<void> {
  await func()
  await sleep(interval)
  callPeriodically(func, interval)
}

/* Cast a string into a proper javascript type. */
/**
 * @param value - String to be cast
* */
export function castString(value: string): any { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (typeof value !== 'string') {
    return value
  }

  try {
    return JSON.parse(value)
  } catch (error) {
    // If there's an error, assume it's just a string.
  }

  return value
}

/* Convert git describe text to a valid URL for the project. */
/**
 * @param func - Function to be called.
 * @param interval - Time in milliseconds to wait after the previous request is done
* */
export function convertGitDescribeToUrl(git_describe: string): string {
  const user = 'bluerobotics'
  const repository = 'blueos-docker'
  const project_url = `https://github.com/${user}/${repository}`

  // Local development version, pointing to root page
  if (!git_describe || git_describe.endsWith('-dirty') || git_describe.length === 0) {
    return project_url
  }

  // Show tag release page
  if (git_describe.startsWith('tags')) {
    const match = /tags\/(?<tag>|.*)-\d-.*/gm.exec(git_describe)
    if (match && match.groups?.tag) {
      const { tag } = match.groups
      return `${project_url}/releases/tag/${tag}`
    }
  }

  // Show git source files page for commit
  const hash = git_describe.slice(git_describe.length - 7)
  return `${project_url}/tree/${hash}`
}
