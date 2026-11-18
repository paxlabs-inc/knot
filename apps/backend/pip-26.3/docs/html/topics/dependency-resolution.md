d loosening the dependencies yourself

```{warning}
If you choose to fork the package yourself, you are _opting out_ of
any support provided by the package maintainers. Proceed at your own risk!
```

#### All requirements are appropriate, but a solution does not exist

Sometimes it's simply impossible to find a combination of package
versions that do not conflict. Welcome to [dependency hell].

In this situation, you could consider:

- Using an alternative package, if that is acceptable for your project.
  See [Awesome Python] for similar packages.
- Refactoring your project to reduce the number of dependencies (for
  example, by breaking up a monolithic code base into smaller pieces).

## Handling Resolution Too Deep Errors

Sometimes pip's dependency resolver may exceed its search depth and terminate
with a `ResolutionTooDeepError` exception. This typically occurs when the
dependency graph is extremely complex or when there are too many package
versions to evaluate.

To address this error, consider the following strategies:

### Specify Reasonable Lower Bounds

By setting a higher lower bound for your dependencies, you narrow the search
space. This excludes older versions that might trigger excessive backtracking.
For example:

```{pip-cli}
$ pip install "package_coffee>=0.44.0" "package_tea>=4.0.0"
```

### Use the `--upgrade` Flag

The `--upgrade` flag directs pip to ignore already installed versions and
search for the latest versions that meet your requirements. This can help
avoid unnecessary resolution paths:

```{pip-cli}
$ pip install --upgrade package_coffee package_tea
```

### Utilize Constraint Files

If you need to impose additional version restrictions on transitive
dependencies (dependencies of dependencies), consider using a constraint
file. A constraint file specifies version limits for packages that are
indirectly required. For example:

```
# constraints.txt
indirect_dependency>=2.0.0
```

Then install your packages with:

```{pip-cli}
$ pip install --constraint constraints.txt package_coffee package_tea
```

### Use Upper Bounds Sparingly

Although upper bounds are generally discouraged because they can complicate
dependency management, they may be necessary when certain versions are known
to cause conflicts. Use them cautiously—for example:

```{pip-cli}
$ pip install "package_coffee>=0.44.0,<1.0.0" "package_tea>=4.0.0"
```

### Report ResolutionTooDeep Errors

If you encounter a `ResolutionTooDeep` error consider reporting it, to help
the pip team have real world examples to test against, at the dedicated
[pip issue](https://github.com/pypa/pip/issues/13281).

## Getting help

If none of the suggestions above work for you, we recommend that you ask
for help on:

- [Python user Discourse](https://discuss.python.org/c/users/7)
- [Python user forums](https://www.python.org/community/forums/)
- [Python developers Slack channel](https://pythondev.slack.com/)
- [Python IRC](https://www.python.org/community/irc/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/python)

See ["How do I ask a good question?"] for tips on asking for help.

Unfortunately, **the pip team cannot provide support for individual
dependency conflict errors**. Please _only_ open a ticket on
[pip's issue tracker](https://github.com/pypa/pip/issues) if you believe
that your problem has exposed a bug in pip.

["how do i ask a good question?"]: https://stackoverflow.com/help/how-to-ask
[awesome python]: https://python.libhunt.com/
[dependency hell]: https://en.wikipedia.org/wiki/Dependency_hell
