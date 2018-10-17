dependency = c(
      'knitr', # for Zeppelin
      'aTSA',
      'dplyr',
      'plyr',
      'magrittr',
      'data.table',
      'sparklyr'
)

install.packages(dependency, repo='http://cloud.r-project.org/')

lapply(dependency, library, character.only = TRUE)

print('R libraries are probably installed by now')