peed=self.speed
            )

    def start(self) -> None:
        """Start the status animation."""
        self._live.start()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._live.stop()

    def __rich__(self) -> RenderableType:
        return self.renderable

    def __enter__(self) -> "Status":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()


if __name__ == "__main__":  # pragma: no cover
    from time import sleep

    from .console import Console

    console = Console()
    with console.status("[magenta]Covid detector booting up") as status:
        sleep(3)
        console.log("Importing advanced AI")
        sleep(3)
        console.log("Advanced Covid AI Ready")
        sleep(3)
        status.update(status="[bold blue] Scanning for Covid", spinner="earth")
        sleep(3)
        console.log("Found 10,000,000,000 copies of Covid32.exe")
        sleep(3)
        status.update(
            status="[bold red]Moving Covid32.exe to Trash",
            spinner="bouncingBall",
            spinner_style="yellow",
        )
        sleep(5)
    console.print("[bold green]Covid deleted successfully")
