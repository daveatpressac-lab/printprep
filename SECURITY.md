# Security

## What printprep does and does not do

printprep reads image files, does arithmetic on them, and writes image files. It makes no network
requests, loads no models, executes nothing from its input, and reads no configuration from the
environment. Its only inputs are the image you hand it and the numbers you pass with it.

The realistic risk is therefore inherited: printprep decodes images through **Pillow** and
**OpenCV**, and both have had memory-safety bugs in their decoders. If you run printprep over
images from people you do not trust, keep those two up to date and treat it as you would any
other image-processing step.

## Supported versions

Only the latest release. The project is at 0.1.0 and there is nothing older to support.

## Reporting a vulnerability

Please report privately rather than in a public issue:

- Use [GitHub's private vulnerability reporting](https://github.com/daveatpressac-lab/printprep/security/advisories/new)
  on this repository.

Please include what you did, what happened, and the printprep, Pillow, OpenCV and Python versions.
A small file or a script that draws one is ideal.

This is a one-person project run in spare time, so I cannot promise a response time. I will
acknowledge a report when I see it, and I would rather hear about something small than not hear
about it at all. If the problem turns out to be in Pillow or OpenCV rather than here, I will say
so and point you at their process.
